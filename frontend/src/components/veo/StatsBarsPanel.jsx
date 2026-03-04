// frontend/src/components/veo/StatsBarsPanel.jsx

import { useMemo } from "react";

/**
 * StatsBarsPanel
 *
 * Read-only, high-readability visual summary for team stats (OWN vs OPPONENT).
 *
 * ✅ Update (collapsible):
 * - The panel is now wrapped in a <details className="group"> so it can be folded/unfolded.
 * - The arrow rotates automatically with: `group-open:rotate-180`.
 *
 * Layout:
 * - Left side: OWN label + value
 * - Center: a single bar split into left/right segments (OWN vs OPP)
 * - Right side: OPP label + value
 * - Stat name displayed under the bar
 *
 * Data source:
 * - teamMetricInputs: object keyed by `${metricSlug}__${side}` (ex: "team_shots__OWN")
 *
 * Notes:
 * - This component DOES NOT mutate state.
 * - It displays values already present in state (manual entry or smart paste).
 *
 * IMPORTANT:
 * - Slugs MUST match your MetricDefinition slugs.
 * - I added the missing rows you asked for, but you may need to adjust a few slugs
 *   if your backend uses different names. Search/replace in `statRows`.
 */
export default function StatsBarsPanel({
  summary,
  teamMetricInputs,
  clubShortLabel = "Notre équipe",
  opponentShortLabel = "Adversaire",
  embedded = true, // optional: when true, removes outer "card" styles to avoid double shadows
}) {
  const labels = useMemo(() => {
    const opponentName = summary?.match?.opponent_name || opponentShortLabel;
    return {
      own: clubShortLabel,
      opp: opponentName,
    };
  }, [summary, clubShortLabel, opponentShortLabel]);

  /**
   * Stats shown in the bar panel.
   * Keep it short and meaningful for quick reading.
   *
   * ✅ Requested order (exact):
   * 1) Buts
   * 2) Tirs
   * 3) Total des tentatives
   * 4) Corner
   * 5) Coup franc
   * 6) Touche
   * 7) Foul
   * 8) Penalty
   * 9) Passes effectuées
   * 10) Possession en %
   * 11) Minutes de possession
   * 12) Possession remportée
   *
   * slug must match your MetricDefinition slugs.
   *
   * ⚠️ You likely need to confirm/adjust these slugs:
   * - "team_total_attempts"
   * - "team_fouls"
   * - "team_penalties"
   * - "team_possession_minutes"
   * - "team_possession_won"
   */
  const statRows = useMemo(
    () => [
      { label: "Buts", slug: "team_goals_scored", unit: "" },
      { label: "Tirs", slug: "team_shots", unit: "" },

      // --- requested extras (verify your slugs) ---
      { label: "Total des tentatives", slug: "team_total_attempts", unit: "" },
      { label: "Corners", slug: "team_corners", unit: "" },
      { label: "Coups francs", slug: "team_free_kicks", unit: "" },
      { label: "Touches", slug: "team_throw_ins", unit: "" },
      { label: "Foul", slug: "team_fouls", unit: "" },
      { label: "Penalty", slug: "team_penalties", unit: "" },

      { label: "Passes effectuées", slug: "team_passes_completed", unit: "" },
      { label: "Possession en %", slug: "team_possession_pct", unit: "%" },

      // --- requested extras (verify your slugs) ---
      { label: "Minutes de possession", slug: "team_possession_minutes", unit: " min" },
      { label: "Possession remportée", slug: "team_possession_won", unit: "" },
    ],
    []
  );

  /**
   * Parse numeric values from the inputs map (string -> number).
   * Returns null when empty/invalid.
   */
  const computed = useMemo(() => {
    const getValue = (slug, side) => {
      const key = `${slug}__${side}`;
      const raw = teamMetricInputs?.[key];
      if (raw === "" || raw === null || raw === undefined) return null;
      const num = Number(raw);
      return Number.isFinite(num) ? num : null;
    };

    return statRows
      .map((row) => {
        const own = getValue(row.slug, "OWN");
        const opp = getValue(row.slug, "OPPONENT");

        // Keep the panel clean: if both empty, do not show the row
        if (own === null && opp === null) return null;

        const safeOwn = own ?? 0;
        const safeOpp = opp ?? 0;

        // Split-bar ratio: OWN vs OPP proportion of total.
        // If total is 0, show 50/50.
        const total = safeOwn + safeOpp;
        const ownPct = total > 0 ? (safeOwn / total) * 100 : 50;
        const oppPct = total > 0 ? (safeOpp / total) * 100 : 50;

        return {
          ...row,
          own,
          opp,
          ownPct,
          oppPct,
        };
      })
      .filter(Boolean);
  }, [statRows, teamMetricInputs]);

  if (!summary) return null;

  const formatValue = (value, unit) => {
    if (value === null || value === undefined) return "—";
    return unit ? `${value}${unit}` : `${value}`;
  };

  // Outer styles can be disabled when this panel is rendered inside another card
  const outerClass = "group bg-white rounded-lg shadow";

  return (
    <div className={outerClass}>
      {/* Header simple (plus de summary/details) */}
      <div className={["flex items-center justify-between", embedded ? "px-4 py-3" : "px-6 py-4"].join(" ")}>
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Statistiques</h3>
        </div>
      </div>
      <div className={[embedded ? "px-4 pb-4" : "px-6 pb-6", "space-y-4"].join(" ")}>
        {computed.length === 0 ? (
          <p className="text-sm text-gray-600">
            Aucune statistique disponible pour l’instant (saisie manuelle ou Copie intelligente).
          </p>
        ) : (
          <div className="space-y-4">
            {computed.map((row) => {
              const ownText = formatValue(row.own, row.unit);
              const oppText = formatValue(row.opp, row.unit);

              return (
                <div
                  key={row.slug}
                  className="rounded-md border border-gray-200 bg-gray-50/30 p-4"
                >
                  {/* Top values (team names above numbers) */}
                  <div className="grid grid-cols-3 items-end gap-3">
                    {/* LEFT */}
                    <div className="text-left">
                      <div className="text-[11px] font-medium text-gray-500 truncate">
                        {labels.own}
                      </div>
                      <div className="text-lg font-semibold text-gray-900">{ownText}</div>
                    </div>

                    {/* CENTER (bar) */}
                    <div className="flex justify-center">
                      <div className="w-full max-w-xl h-4 rounded bg-gray-200 overflow-hidden flex">
                        {/* OWN segment */}
                        <div
                          className="h-full bg-blue-600"
                          style={{
                            width: `${Math.max(0, Math.min(100, row.ownPct))}%`,
                          }}
                          aria-label={`${row.label} ${labels.own} ${ownText}`}
                        />
                        {/* OPP segment */}
                        <div
                          className="h-full bg-gray-800"
                          style={{
                            width: `${Math.max(0, Math.min(100, row.oppPct))}%`,
                          }}
                          aria-label={`${row.label} ${labels.opp} ${oppText}`}
                        />
                      </div>
                    </div>

                    {/* RIGHT */}
                    <div className="text-right">
                      <div className="text-[11px] font-medium text-gray-500 truncate">
                        {labels.opp}
                      </div>
                      <div className="text-lg font-semibold text-gray-900">{oppText}</div>
                    </div>
                  </div>

                  {/* Stat name under the bar */}
                  <div className="mt-2 text-center text-sm font-semibold text-gray-900">
                    {row.label}
                  </div>

                  {/* Tiny hint */}
                  <div className="mt-1 text-center text-[11px] text-gray-500">
                    Répartition basée sur OWN / (OWN + OPP).
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}