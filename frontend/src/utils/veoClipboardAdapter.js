/**
 * veoClipboardAdapter.js
 *
 * Frontend adapter that converts backend VEO clipboard parsing results into
 * safe, UI-ready patches for the existing VEO metrics form.
 *
 * Why this file exists:
 * - Backend parsers are "source of truth" and must not be modified.
 * - Frontend needs a deterministic mapping from parsed output -> metric slugs.
 * - We avoid writing anything unknown/unmapped to the form to reduce user errors.
 *
 * Supported parser outputs (as returned by POST /parse-veo-clipboard):
 * - type: "statistiques"
 * - type: "carte_des_tirs"
 * - type: "zone_de_passes"
 * - type: "zone_de_possession"
 * - type: "enchaînements_collectifs"
 *
 * Important:
 * - This module ONLY prepares patches (it does not call the API and does not save).
 * - Unknown labels/fields become warnings (never silently mapped).
 */

/**
 * Build a unique input key used by Veo.jsx for team metrics inputs.
 * The current page uses: `${slug}__${side}`
 *
 * @param {string} slug
 * @param {"OWN"|"OPPONENT"} side
 * @returns {string}
 */
export function makeTeamMetricKey(slug, side) {
  return `${slug}__${side}`;
}

/**
 * Parse a VEO number-like value.
 * Accepts:
 *  - "37%" => 37
 *  - "38.5%" => 38.5
 *  - "14" => 14
 *  - "14.2" => 14.2
 *
 * Returns null when invalid (safe behavior).
 *
 * @param {string|number|null|undefined} raw
 * @returns {number|null}
 */
export function parseVeoNumericValue(raw) {
  if (raw === null || raw === undefined) return null;

  const text = String(raw).trim();
  if (!text) return null;

  const normalized = text.replace(",", "."); // just in case
  const isPercent = normalized.endsWith("%");
  const numPart = isPercent ? normalized.slice(0, -1) : normalized;

  // Strict numeric format
  if (!/^\d+(\.\d+)?$/.test(numPart)) return null;

  const value = Number(numPart);
  if (Number.isNaN(value)) return null;

  return value;
}

/**
 * Build a set of known metric slugs from the entry schema.
 *
 * @param {any} entrySchema - Response from GET /metrics/entry-schema
 * @returns {Set<string>}
 */
export function buildKnownMetricSlugSet(entrySchema) {
  const slugs = new Set();

  const teamGroups = entrySchema?.team_metrics_by_category ?? [];
  const playerGroups = entrySchema?.player_metrics_by_category ?? [];

  teamGroups.forEach((group) => {
    (group?.metrics ?? []).forEach((m) => {
      if (m?.slug) slugs.add(m.slug);
    });
  });

  playerGroups.forEach((group) => {
    (group?.metrics ?? []).forEach((m) => {
      if (m?.slug) slugs.add(m.slug);
    });
  });

  return slugs;
}

/**
 * Internal: map VEO labels (from "Statistiques" clipboard parser) to team metric slugs.
 * Keep this mapping explicit and conservative.
 *
 * If a slug does not exist in the entry schema, we will warn and skip it.
 *
 * Notes:
 * - Some opponent metrics are stored using the same slug with side=OPPONENT.
 * - Some are stored using a dedicated "conceded" slug (goals/shots in your UI).
 */
const STAT_LABEL_TO_TEAM_METRIC = {
  // label -> { ownSlug, opponentSlug? }
  But: { ownSlug: "team_goals_scored", opponentSlug: "team_goals_conceded" },
  Tir: { ownSlug: "team_shots", opponentSlug: "team_shots_conceded" },
  Corner: { ownSlug: "team_corners" },
  "Coup franc": { ownSlug: "team_free_kicks" },
  "Passes effectuées": { ownSlug: "team_passes_completed" },
  "Possession en %": { ownSlug: "team_possession_pct" },

  // Optional / depends if your catalog contains those slugs:
  "Total des tentatives": { ownSlug: "team_total_attempts" },
  Penalty: { ownSlug: "team_penalties" },
  "Minutes de possession": { ownSlug: "team_possession_minutes" },
  "Possession remportée": { ownSlug: "team_possession_won" },

  // Your whitelist currently uses "Throw-in" (English label) — if your catalog uses a different slug, adjust here:
  "Throw-in": { ownSlug: "team_throw_ins" },
};

/**
 * Internal: map VEO labels (from "Carte des tirs" clipboard parser) to team metric slugs.
 */
const SHOTMAP_LABEL_TO_TEAM_METRIC = {
  Buts: { ownSlug: "team_goals_scored", opponentSlug: "team_goals_conceded" },
  Tirs: { ownSlug: "team_shots", opponentSlug: "team_shots_conceded" },
  "Total des tentatives": { ownSlug: "team_total_attempts" },
};

/**
 * Create safe patches for teamMetricInputs based on parsed clipboard results.
 *
 * Returned patches are a list of:
 *  - { key: "metric_slug__SIDE", value: number }
 *
 * @param {Object} params
 * @param {{type: string, data: any}} params.parsed - API response from /parse-veo-clipboard
 * @param {any} params.entrySchema - entry schema used to validate metric slugs
 * @returns {{
 *   teamMetricPatches: Array<{key: string, value: number}>,
 *   warnings: string[],
 *   rawPreview: any
 * }}
 */
export function buildClipboardApplyPlan({ parsed, entrySchema }) {
  const warnings = [];
  const teamMetricPatches = [];

  if (!parsed || !parsed.type) {
    return {
      teamMetricPatches,
      warnings: ["Clipboard parsing result is missing 'type'."],
      rawPreview: parsed ?? null,
    };
  }

  const knownSlugs = buildKnownMetricSlugSet(entrySchema);

  /**
   * Helper to push a metric patch only if:
   * - value is a valid number
   * - slug exists in schema
   */
  const pushPatchIfValid = ({ slug, side, value, labelHint }) => {
    if (!slug || !side) return;

    if (!knownSlugs.has(slug)) {
      warnings.push(
        `Metric slug '${slug}' is not present in entry schema (skipped).` +
          (labelHint ? ` Source: ${labelHint}` : ""),
      );
      return;
    }

    if (typeof value !== "number" || Number.isNaN(value)) {
      warnings.push(
        `Invalid numeric value for '${slug}' (${side}) (skipped).` +
          (labelHint ? ` Source: ${labelHint}` : ""),
      );
      return;
    }

    teamMetricPatches.push({
      key: makeTeamMetricKey(slug, side),
      value,
    });
  };

  // =========================
  // Case: STATISTIQUES
  // =========================
  if (parsed.type === "statistiques") {
    // Expected parser format:
    // {
    //   equipe: "TEG",
    //   adversaire: "UST",
    //   stats: {
    //     "But": { "TEG": "1", "UST": "0" },
    //     "Possession en %": { "TEG": "37%", "UST": "63%" }
    //   }
    // }
    const data = parsed.data ?? {};
    const stats = data.stats ?? {};
    const teamShort = data.equipe;
    const oppShort = data.adversaire;

    if (!teamShort || !oppShort) {
      warnings.push("Missing 'equipe'/'adversaire' in statistiques payload.");
      return { teamMetricPatches, warnings, rawPreview: parsed };
    }

    Object.entries(stats).forEach(([label, perTeam]) => {
      const mapping = STAT_LABEL_TO_TEAM_METRIC[label];
      if (!mapping) {
        warnings.push(`Unmapped statistiques label '${label}' (skipped).`);
        return;
      }

      const ownRaw = perTeam?.[teamShort];
      const oppRaw = perTeam?.[oppShort];

      const ownVal = parseVeoNumericValue(ownRaw);
      const oppVal = parseVeoNumericValue(oppRaw);

      // Own
      if (ownVal !== null) {
        pushPatchIfValid({
          slug: mapping.ownSlug,
          side: "OWN",
          value: ownVal,
          labelHint: `statistiques:${label}`,
        });
      } else if (ownRaw !== undefined) {
        warnings.push(`Could not parse value '${ownRaw}' for '${label}' (OWN).`);
      }

      // Opponent
      // If opponentSlug exists, use it with side=OPPONENT.
      // Otherwise use the same slug with side=OPPONENT (mirrored metrics).
      const oppSlug = mapping.opponentSlug || mapping.ownSlug;

      if (oppVal !== null) {
        pushPatchIfValid({
          slug: oppSlug,
          side: "OPPONENT",
          value: oppVal,
          labelHint: `statistiques:${label}`,
        });
      } else if (oppRaw !== undefined) {
        warnings.push(`Could not parse value '${oppRaw}' for '${label}' (OPPONENT).`);
      }
    });

    return { teamMetricPatches, warnings, rawPreview: parsed };
  }

  // =========================
  // Case: CARTE DES TIRS
  // =========================
  if (parsed.type === "carte_des_tirs") {
    // Expected parser format:
    // {
    //   type: "carte_des_tirs",
    //   data: { "Buts": "1", "Tirs": "10", "Total des tentatives": "11", ... }
    // }
    const data = parsed.data?.data ?? parsed.data ?? {};
    // Your shotmap_parser returns { type:"carte_des_tirs", data:{...} } BUT
    // your endpoint wraps it as { type: menu_type, data: parsed }.
    // So we support both shapes above.

    Object.entries(data).forEach(([label, rawValue]) => {
      const mapping = SHOTMAP_LABEL_TO_TEAM_METRIC[label];
      if (!mapping) {
        // Shotmap also includes phrase keys (conversion_rate etc) → ignore but show warning
        warnings.push(`Unmapped shotmap key '${label}' (kept in preview only).`);
        return;
      }

      const ownVal = parseVeoNumericValue(rawValue);
      if (ownVal === null) {
        warnings.push(`Could not parse value '${rawValue}' for shotmap label '${label}'.`);
        return;
      }

      pushPatchIfValid({
        slug: mapping.ownSlug,
        side: "OWN",
        value: ownVal,
        labelHint: `carte_des_tirs:${label}`,
      });

      // We cannot infer opponent values from shotmap parser output.
      // So we only patch OWN side here.
    });

    return { teamMetricPatches, warnings, rawPreview: parsed };
  }

  // =========================
  // Zone de passes / possession / enchaînements
  // =========================
  // For these menus, your current VEO metrics catalog might not include matching slugs yet.
  // We return preview + warnings, but do not patch unknown fields.
  if (
    parsed.type === "zone_de_passes" ||
    parsed.type === "zone_de_possession" ||
    parsed.type === "enchaînements_collectifs"
  ) {
    warnings.push(
      `Clipboard type '${parsed.type}' parsed successfully, but no metric slug mapping is configured yet.`,
    );
    return { teamMetricPatches, warnings, rawPreview: parsed };
  }

  // Unknown type
  warnings.push(`Unsupported clipboard type '${parsed.type}'.`);
  return { teamMetricPatches, warnings, rawPreview: parsed };
}
