// frontend/src/components/SmartPastePanel.jsx

import { useMemo, useState } from "react";
import { clipboardService } from "../../services/clipboardService";

/**
 * SmartPastePanel
 *
 * UI helper that lets coaches paste raw text copied from VEO menus and
 * apply deterministic mappings into the current match team metrics inputs.
 *
 * Design goals:
 * - Backend parsers are the single source of truth (frontend only calls the API).
 * - Allow explicit menu selection to reduce user mistakes.
 * - Preview parsed data before applying it.
 * - Apply only safe, deterministic mappings to known team metric slugs.
 *
 * Current mapping support:
 * - "statistiques"  -> team metrics (OWN/OPPONENT)
 * - "carte_des_tirs" -> team metrics (OWN only)
 *
 * Preview-only (no mapping applied yet):
 * - "zone_de_passes"
 * - "zone_de_possession"
 * - "enchaînements_collectifs"
 *
 * Note:
 * - This component only updates `teamMetricInputs` via `setTeamMetricInputs`.
 * - It does NOT persist to backend; user still clicks "Enregistrer metriques equipe".
 */

/**
 * @typedef {Object} SmartPastePanelProps
 * @property {Object|null} entrySchema - Backend entry schema used to know which team metric slugs exist.
 * @property {number} selectedMatchId - Current match id (must be a valid number).
 * @property {(updater: any) => void} setTeamMetricInputs - State setter from Veo page.
 * @property {(message: string, type?: "success"|"error") => void} setFlash - Flash helper from Veo page.
 */

/**
 * Internal helper to build the same key format as Veo.jsx.
 * @param {string} slug
 * @param {"OWN"|"OPPONENT"} side
 * @returns {string}
 */
function makeTeamMetricKey(slug, side) {
  return `${slug}__${side}`;
}

/**
 * Convert VEO string values (e.g. "37%", "38,5%", "175") into a safe numeric string
 * for HTML numeric inputs.
 *
 * @param {string|number|null|undefined} value
 * @returns {string|null} A normalized numeric string, or null if invalid.
 */
function normalizeVeoValueToInputNumberString(value) {
  if (value === null || value === undefined) return null;

  const raw = String(value).trim();
  if (!raw) return null;

  const cleaned = raw.replace(/\s+/g, "").replace(",", ".").replace("%", "");
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return null;

  return cleaned;
}

/**
 * Pretty-print object for preview.
 * @param {any} data
 * @returns {string}
 */
function prettyJson(data) {
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
}

/**
 * IMPORTANT:
 * The `key` MUST match the backend `menu_type` returned by /parse-veo-clipboard.
 */
const MENU_OPTIONS = [
  { key: "statistiques", label: "Statistiques" },
  { key: "carte_des_tirs", label: "Carte des tirs" },
  { key: "zone_de_passes", label: "Zone de passes" },
  { key: "zone_de_possession", label: "Zone de possession" },
  { key: "enchaînements_collectifs", label: "Enchainements collectifs" },
];

/**
 * Deterministic mappings for team metrics based on your existing Veo.jsx slugs.
 *
 * Important:
 * - For goals/shots: Veo.jsx uses a single input slug for both sides and maps
 *   OPPONENT side to a different "saveSlug" in handleSaveTeamMetrics.
 *   So we must set keys for inputSlug:
 *     - team_goals_scored__OWN = our goals
 *     - team_goals_scored__OPPONENT = opponent goals (becomes conceded on save)
 *     - team_shots__OWN = our shots
 *     - team_shots__OPPONENT = opponent shots (becomes conceded on save)
 */
const STAT_LABEL_TO_INPUT_SLUG = {
  // ✅ Buts
  But: { inputSlug: "team_goals_scored" },
  Buts: { inputSlug: "team_goals_scored" },

  // ✅ Tirs
  Tir: { inputSlug: "team_shots" },
  Tirs: { inputSlug: "team_shots" },

  // ✅ Total des tentatives
  "Total des tentatives": { inputSlug: "team_total_attempts" },
  "Total tentatives": { inputSlug: "team_total_attempts" },
  Tentatives: { inputSlug: "team_total_attempts" },

  // ✅ Corners
  Corner: { inputSlug: "team_corners" },
  Corners: { inputSlug: "team_corners" },

  // ✅ Coups francs
  "Coup franc": { inputSlug: "team_free_kicks" },
  "Coups francs": { inputSlug: "team_free_kicks" },

  // ✅ Touches
  Touche: { inputSlug: "team_throw_ins" },
  Touches: { inputSlug: "team_throw_ins" },
  "Throw-in": { inputSlug: "team_throw_ins" },
  "Throw-ins": { inputSlug: "team_throw_ins" },

  // ✅ Fautes
  Foul: { inputSlug: "team_fouls" },
  Fouls: { inputSlug: "team_fouls" },
  Faute: { inputSlug: "team_fouls" },
  Fautes: { inputSlug: "team_fouls" },

  // ✅ Penalty
  Penalty: { inputSlug: "team_penalties" },
  Penalties: { inputSlug: "team_penalties" },
  Penaltys: { inputSlug: "team_penalties" }, // au cas où (souvent mal écrit)

  // ✅ Passes
  "Passes effectuées": { inputSlug: "team_passes_completed" },
  "Passes réussies": { inputSlug: "team_passes_completed" },

  // ✅ Possession %
  "Possession en %": { inputSlug: "team_possession_pct" },
  "Possession %": { inputSlug: "team_possession_pct" },
  Possession: { inputSlug: "team_possession_pct" },

  // ✅ Minutes de possession
  "Minutes de possession": { inputSlug: "team_possession_minutes" },

  // ✅ Possession remportée
  "Possession remportée": { inputSlug: "team_possession_won" },
};

const SHOTMAP_LABEL_TO_INPUT_SLUG = {
  Buts: { inputSlug: "team_goals_scored" },
  Tirs: { inputSlug: "team_shots" },
  "Total des tentatives": { inputSlug: "team_total_attempts" },

  // percent phrases -> backend slugs (returned as keys)
  team_shotmap_conversion_rate_pct: { inputSlug: "team_shotmap_conversion_rate_pct" },
  team_shotmap_inside_box_conversion_rate_pct: { inputSlug: "team_shotmap_inside_box_conversion_rate_pct" },
  team_shotmap_outside_box_conversion_rate_pct: { inputSlug: "team_shotmap_outside_box_conversion_rate_pct" },
  team_shotmap_attempts_inside_box_pct: { inputSlug: "team_shotmap_attempts_inside_box_pct" },
  team_shotmap_attempts_outside_box_pct: { inputSlug: "team_shotmap_attempts_outside_box_pct" },
};

export default function SmartPastePanel({
  entrySchema,
  selectedMatchId,
  setTeamMetricInputs,
  setFlash,
  onParsedChange,
}) {
  const [isOpen, setIsOpen] = useState(false);

  const [selectedMenu, setSelectedMenu] = useState("statistiques");
  const [clubPrefix, setClubPrefix] = useState("TEG");
  const [rawText, setRawText] = useState("");

  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [parsed, setParsed] = useState(null); // { type, data }
  const [lastAppliedSummary, setLastAppliedSummary] = useState("");

  // Hooks must ALWAYS run before any conditional return.
  const knownTeamMetricSlugs = useMemo(() => {
    const groups = entrySchema?.team_metrics_by_category ?? [];
    const slugs = new Set();
    for (const group of groups) {
      for (const metric of group.metrics ?? []) {
        if (metric?.slug) slugs.add(metric.slug);
      }
    }
    return slugs;
  }, [entrySchema]);

  const detectedTypeLabel = useMemo(() => {
    if (!parsed?.type) return "";
    const found = MENU_OPTIONS.find((opt) => opt.key === parsed.type);
    return found?.label || parsed.type;
  }, [parsed]);

  const canRender = Number.isFinite(selectedMatchId) && selectedMatchId > 0;
  if (!canRender) return null;

  const handleParse = async () => {
    setParseError("");
    setParsed(null);
    setLastAppliedSummary("");

    const safeText = String(rawText || "").trim();
    if (safeText.length < 10) {
      setParseError("Le texte colle est trop court.");
      return;
    }

    try {
      setParsing(true);
      const result = await clipboardService.parseVeoClipboard({
        text: safeText,
        clubPrefix: clubPrefix || "TEG",
        menuType: selectedMenu,
      });

      setParsed(result);
      onParsedChange?.(result);

      if (result?.type && result.type !== selectedMenu) {
        setFlash(
          `Attention: menu detecte "${result.type}" (tu as selectionne "${selectedMenu}"). Preview disponible avant application.`,
          "error"
        );
      } else {
        setFlash("Collage analyse avec succes.");
      }
    } catch (err) {
      setParseError(err?.message || "Erreur pendant le parsing.");
      setFlash(err?.message || "Erreur pendant le parsing.", "error");
    } finally {
      setParsing(false);
    }
  };

  const handleApply = () => {
    if (!parsed?.type || !parsed?.data) {
      setFlash("Aucune donnee a appliquer. Fais d'abord 'Analyser'.", "error");
      return;
    }

    const detectedType = parsed.type;
    const canApply = detectedType === "statistiques" || detectedType === "carte_des_tirs";

    if (!canApply) {
      setFlash(
        `Le menu "${detectedType}" est en mode preview uniquement (mapping non implemente).`,
        "error"
      );
      return;
    }

    const updates = {};
    const applied = [];
    const skipped = [];

    const setIfValidAndKnown = (inputSlug, side, value) => {
      if (!inputSlug || !side) return;

      if (!knownTeamMetricSlugs.has(inputSlug)) {
        skipped.push(`${inputSlug} (${side}) - slug inconnu`);
        return;
      }

      const normalized = normalizeVeoValueToInputNumberString(value);
      if (normalized === null) {
        skipped.push(`${inputSlug} (${side}) - valeur invalide: ${String(value)}`);
        return;
      }

      updates[makeTeamMetricKey(inputSlug, side)] = normalized;
      applied.push(`${inputSlug} (${side}) = ${normalized}`);
    };

    if (detectedType === "statistiques") {
      const stats = parsed.data?.stats || {};
      const ownTeamName = parsed.data?.equipe;
      const oppTeamName = parsed.data?.adversaire;

      for (const [label, teamValues] of Object.entries(stats)) {
        const mapping = STAT_LABEL_TO_INPUT_SLUG[label];
        if (!mapping?.inputSlug) continue;

        const ownValue = teamValues?.[ownTeamName];
        const oppValue = teamValues?.[oppTeamName];

        if (ownValue !== undefined) setIfValidAndKnown(mapping.inputSlug, "OWN", ownValue);
        if (oppValue !== undefined) setIfValidAndKnown(mapping.inputSlug, "OPPONENT", oppValue);
      }
    }

    if (detectedType === "carte_des_tirs") {
      // Endpoint returns { type: menu_type, data: parsed }
      // shotmap_parser returns { type: "carte_des_tirs", data: {...} }
      // Here we accept both shapes safely.
      const innerData = parsed.data?.data || parsed.data || {};
      for (const [label, value] of Object.entries(innerData)) {
        const mapping = SHOTMAP_LABEL_TO_INPUT_SLUG[label];
        if (!mapping?.inputSlug) continue;

        // Only OWN side is safe to auto-fill for shotmap.
        setIfValidAndKnown(mapping.inputSlug, "OWN", value);
      }
    }

    if (Object.keys(updates).length === 0) {
      setFlash("Aucune metrique applicable detectee dans ce collage.", "error");
      return;
    }

    setTeamMetricInputs((prev) => ({
      ...prev,
      ...updates,
    }));

    const summary =
      `Applique: ${applied.length} • Ignore: ${skipped.length}` +
      (skipped.length ? ` (ex: ${skipped[0]})` : "");

    setLastAppliedSummary(summary);
    setFlash("Valeurs appliquees dans le formulaire. Pense a enregistrer ensuite.");
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Copie intelligente</h3>
          <p className="mt-1 text-sm text-gray-600">
            Colle le texte brut depuis VEO. Le backend detecte automatiquement le menu et renvoie un format structure.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen((v) => !v)}
          className="inline-flex items-center justify-center px-3 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
        >
          {isOpen ? "Fermer" : "Ouvrir"}
        </button>
      </div>

      {!isOpen ? null : (
        <div className="mt-5 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {MENU_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => {
                  setSelectedMenu(opt.key);
                  setParsed(null);
                  setParseError("");
                  setLastAppliedSummary("");
                }}
                className={`px-3 py-2 rounded-md text-sm font-medium border ${
                  selectedMenu === opt.key
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <label className="block">
              <span className="text-xs font-medium text-gray-600">Prefixe club (Statistiques)</span>
              <input
                className="mt-1 w-full h-10 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={clubPrefix}
                onChange={(e) => setClubPrefix(e.target.value)}
                placeholder="Ex: TEG"
              />
              <p className="mt-1 text-[11px] text-gray-500">
                Utilise pour identifier ton equipe dans le collage “Statistiques”.
              </p>
            </label>

            <div className="lg:col-span-2 flex items-end gap-2">
              <button
                type="button"
                onClick={handleParse}
                disabled={parsing}
                className="h-10 px-4 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {parsing ? "Analyse..." : "Analyser"}
              </button>

              <button
                type="button"
                onClick={handleApply}
                disabled={!parsed || parsing}
                className="h-10 px-4 rounded-md text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Appliquer au formulaire
              </button>

              <button
                type="button"
                onClick={() => {
                  setRawText("");
                  setParsed(null);
                  onParsedChange?.(null);
                  setParseError("");
                  setLastAppliedSummary("");
                }}
                className="h-10 px-4 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Vider
              </button>
            </div>
          </div>

          <div>
            <label className="block">
              <span className="text-xs font-medium text-gray-600">
                Texte colle (menu: {MENU_OPTIONS.find((m) => m.key === selectedMenu)?.label})
              </span>
              <textarea
                className="mt-1 w-full min-h-40 border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Colle ici le texte depuis VEO..."
              />
            </label>
          </div>

          {parseError ? (
            <div className="rounded-md bg-red-50 p-3 border border-red-100">
              <p className="text-sm text-red-800">{parseError}</p>
            </div>
          ) : null}

          {lastAppliedSummary ? (
            <div className="rounded-md bg-emerald-50 p-3 border border-emerald-100">
              <p className="text-sm text-emerald-800">{lastAppliedSummary}</p>
              <p className="mt-1 text-xs text-emerald-700">
                Les champs ont ete remplis dans la grille. Clique ensuite sur “Enregistrer metriques equipe”.
              </p>
            </div>
          ) : null}

          <div className="border rounded-md overflow-hidden">
            <div className="px-3 py-2 bg-gray-50 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <p className="text-sm font-medium text-gray-800">Preview parsing</p>
              <div className="text-xs text-gray-600">
                {parsed?.type ? (
                  <>
                    Type detecte: <span className="font-semibold">{detectedTypeLabel}</span>
                    {parsed.type !== selectedMenu ? (
                      <span className="ml-2 text-red-600">(differe de la selection)</span>
                    ) : null}
                  </>
                ) : (
                  "Aucune donnee (colle puis clique sur Analyser)"
                )}
              </div>
            </div>

            {parsed ? (
              <pre className="p-3 text-xs overflow-auto bg-white">{prettyJson(parsed)}</pre>
            ) : (
              <div className="p-3 text-sm text-gray-500">
                Colle le texte puis clique sur <span className="font-medium">Analyser</span>.
              </div>
            )}
          </div>

          <div className="rounded-md bg-blue-50 border border-blue-100 p-3">
            <p className="text-sm text-blue-900 font-semibold">Mappages disponibles</p>
            <ul className="mt-2 text-sm text-blue-900 list-disc pl-5 space-y-1">
              <li>
                <span className="font-medium">Statistiques</span> : But(s), Tir(s), Total des tentatives, Possession %, Minutes de possession,
                Possession remportée, Corner(s), Coup(s) franc(s), Foul(s)/Fautes, Penalty(s), Passes effectuées, Throw-in/Touche
              </li>
              <li>
                <span className="font-medium">Carte des tirs</span> : Buts, Tirs (cote OWN uniquement)
              </li>
              <li>
                Zones et enchainements : <span className="font-medium">preview uniquement</span> pour l’instant.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}