// frontend/src/components/ShotmapOverview.jsx
import { useMemo } from "react";

/**
 * ShotmapOverview
 *
 * Visual summary for VEO "carte_des_tirs" parsed data (no shot coordinates).
 * Shows:
 * - KPIs (goals, shots, total attempts, conversion)
 * - Half-pitch SVG with highlighted zones (inside box vs outside)
 * - Simple stacked bar for attempts distribution
 * - Simple bar for conversion rates inside/outside
 *
 * Props:
 * - parsedShotmap: the full response returned by /parse-veo-clipboard for "carte_des_tirs"
 *   Example shape:
 *   {
 *     type: "carte_des_tirs",
 *     data: {
 *       type: "carte_des_tirs",
 *       data: { ...metrics }
 *     }
 *   }
 */
export default function ShotmapOverview({ parsedShotmap, embedded = false }) {
  const detectedType = parsedShotmap?.type ?? parsedShotmap?.data?.type ?? null;
  const inner =
    parsedShotmap?.data?.data ??
    parsedShotmap?.data ??
    parsedShotmap?.data?.data?.data ??
    {};
  // inner keys are the ones you want:
  // "Buts", "Tirs", "Total des tentatives", and team_shotmap_* keys.

  const metrics = useMemo(() => {
    const toInt = (v) => {
      const n = parseInt(String(v ?? "").trim(), 10);
      return Number.isFinite(n) ? n : 0;
    };

    const toPct = (v) => {
      // "40%" -> 40, "38.5%" -> 38.5
      const s = String(v ?? "").trim().replace(",", ".").replace("%", "");
      const n = Number(s);
      return Number.isFinite(n) ? n : 0;
    };

    const goals = toInt(inner["Buts"]);
    const shots = toInt(inner["Tirs"]);
    const totalAttempts = toInt(inner["Total des tentatives"]);

    const conv = toPct(inner["team_shotmap_conversion_rate_pct"]);
    const convIn = toPct(inner["team_shotmap_inside_box_conversion_rate_pct"]);
    const convOut = toPct(inner["team_shotmap_outside_box_conversion_rate_pct"]);

    const attemptsIn = toPct(inner["team_shotmap_attempts_inside_box_pct"]);
    const attemptsOut = toPct(inner["team_shotmap_attempts_outside_box_pct"]);

    // Normalize if data is weird (e.g., doesn't sum to 100)
    const sumAttempts = attemptsIn + attemptsOut;
    const safeAttemptsIn = sumAttempts > 0 ? (attemptsIn / sumAttempts) * 100 : 0;
    const safeAttemptsOut = sumAttempts > 0 ? (attemptsOut / sumAttempts) * 100 : 0;

    return {
      goals,
      shots,
      totalAttempts,
      conv,
      convIn,
      convOut,
      attemptsIn: safeAttemptsIn,
      attemptsOut: safeAttemptsOut,
    };
  }, [parsedShotmap]);

  const clamp01 = (x) => Math.max(0, Math.min(100, x));

  const attemptsInW = clamp01(metrics.attemptsIn);
  const attemptsOutW = clamp01(metrics.attemptsOut);

  const convInW = clamp01(metrics.convIn);
  const convOutW = clamp01(metrics.convOut);

  const showEmpty = !parsedShotmap || detectedType !== "carte_des_tirs";

  return (
    <div className={embedded ? "" : "bg-white rounded-lg shadow p-6"}>
      {/* Header simple (plus de summary/details) */}
      <div className={["flex items-center justify-between", embedded ? "px-4 py-3" : "px-6 py-4"].join(" ")}>
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Carte des tirs</h3>
          <p className="mt-1 text-sm text-gray-600">
            Résumé visuel “Carte des tirs” (agrégé). Pas de positions exactes des tirs.
          </p>
        </div>
      </div>

      <div className={[embedded ? "pt-4" : "px-6 pb-6", "space-y-4"].join(" ")}>
        {showEmpty ? (
          <div className="rounded-md border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
            Colle et analyse une <span className="font-medium">Carte des tirs</span> pour afficher le résumé.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* KPIs */}
            <div className="lg:col-span-1 grid grid-cols-2 gap-3">
              <KpiCard label="Buts" value={metrics.goals} />
              <KpiCard label="Tirs" value={metrics.shots} />
              <KpiCard label="Total tentatives" value={metrics.totalAttempts} />
              <KpiCard label="Conversion" value={`${metrics.conv}%`} />
            </div>

            {/* Pitch */}
            <div className="lg:col-span-2 rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-800">Répartition & zones</p>
                <div className="text-xs text-gray-600">
                  Dans la surface:{" "}
                  <span className="font-semibold">{Math.round(metrics.attemptsIn)}%</span> • Hors de la
                  surface:
                  <span className="font-semibold"> {Math.round(metrics.attemptsOut)}%</span>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-1 xl:grid-cols-2 gap-4">
                <div className="space-y-4">
                  {/* Attempts distribution */}
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800">Répartition des tentatives</p>
                      <p className="text-xs text-gray-600">
                        {Math.round(attemptsInW)}% / {Math.round(attemptsOutW)}%
                      </p>
                    </div>

                    <StackedBar
                      leftLabel="Dans la surface"
                      rightLabel="Hors de la surface"
                      leftPct={attemptsInW}
                      rightPct={attemptsOutW}
                    />
                  </div>

                  {/* Conversion comparison */}
                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800">Conversion par zone</p>
                      <p className="text-xs text-gray-600">
                        Dans la surface de réparation {Math.round(convInW)}% • Hors de la surface de
                        réparation {Math.round(convOutW)}%
                      </p>
                    </div>

                    <CompareBars
                      aLabel="Dans la surface de réparation"
                      aPct={convInW}
                      bLabel="Hors de la surface de réparation"
                      bPct={convOutW}
                    />
                  </div>

                  <div className="rounded-md bg-blue-50 border border-blue-100 p-3">
                    <p className="text-sm text-blue-900 font-semibold">Lecture coach</p>
                    <ul className="mt-2 text-sm text-blue-900 list-disc pl-5 space-y-1">
                      <li>
                        <span className="font-medium">Volume</span> : tirs & tentatives pour mesurer
                        l’intention offensive.
                      </li>
                      <li>
                        <span className="font-medium">Qualité</span> : dans la surface % indique si
                        l’équipe arrive à entrer dans la surface.
                      </li>
                      <li>
                        <span className="font-medium">Efficacité</span> : conversion globale + par
                        zone pour orienter les séances (finition / création).
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function StackedBar({ leftLabel, rightLabel, leftPct, rightPct }) {
  const leftW = Math.max(0, Math.min(100, leftPct));
  const rightW = Math.max(0, Math.min(100, rightPct));

  return (
    <div className="mt-2">
      <div className="h-3 w-full rounded-full overflow-hidden border border-gray-200 bg-gray-100 flex">
        <div
          className="h-full bg-emerald-500"
          style={{ width: `${leftW}%` }}
          title={`${leftLabel}: ${Math.round(leftW)}%`}
        />
        <div
          className="h-full bg-indigo-500"
          style={{ width: `${rightW}%` }}
          title={`${rightLabel}: ${Math.round(rightW)}%`}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-gray-600">
        <span className="inline-flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-sm bg-emerald-500" />
          {leftLabel}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-sm bg-indigo-500" />
          {rightLabel}
        </span>
      </div>
    </div>
  );
}

function CompareBars({ aLabel, aPct, bLabel, bPct }) {
  const aW = Math.max(0, Math.min(100, aPct));
  const bW = Math.max(0, Math.min(100, bPct));

  return (
    <div className="mt-2 space-y-2">
      <MiniBar label={aLabel} pct={aW} colorClass="bg-emerald-500" />
      <MiniBar label={bLabel} pct={bW} colorClass="bg-indigo-500" />
    </div>
  );
}

function MiniBar({ label, pct, colorClass }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className="font-medium">{Math.round(pct)}%</span>
      </div>
      <div className="mt-1 h-2 w-full rounded-full overflow-hidden border border-gray-200 bg-gray-100">
        <div className={`h-full ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/**
 * Half-pitch SVG with:
 * - goal + box
 * - zone overlays: inside box vs outside
 * - little labels with attempts + conversion
 */
function PitchHalf({ attemptsInPct, attemptsOutPct, convInPct, convOutPct }) {
  // Simple half-pitch coordinate system
  // ViewBox: 0 0 100 70 (width x height)
  // Goal at bottom center (y ~ 68), attacking upwards.
  const inPct = Math.round(Math.max(0, Math.min(100, attemptsInPct)));
  const outPct = Math.round(Math.max(0, Math.min(100, attemptsOutPct)));
  const cin = Math.round(Math.max(0, Math.min(100, convInPct)));
  const cout = Math.round(Math.max(0, Math.min(100, convOutPct)));

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <svg viewBox="0 0 100 70" className="w-full h-auto">
        {/* Pitch background */}
        <rect x="2" y="2" width="96" height="66" rx="4" className="fill-white stroke-gray-300" strokeWidth="1.2" />

        {/* Midline (top border of half pitch) */}
        <line x1="2" y1="2" x2="98" y2="2" className="stroke-gray-300" strokeWidth="1" />

        {/* Penalty box */}
        <rect x="22" y="38" width="56" height="30" className="fill-transparent stroke-gray-400" strokeWidth="1" />
        {/* Six-yard box */}
        <rect x="35" y="54" width="30" height="14" className="fill-transparent stroke-gray-400" strokeWidth="1" />
        {/* Penalty spot */}
        <circle cx="50" cy="50" r="1.2" className="fill-gray-400" />
        {/* Arc */}
        <path d="M 38 50 A 12 12 0 0 1 62 50" className="fill-transparent stroke-gray-400" strokeWidth="1" />

        {/* Goal */}
        <rect x="44" y="66" width="12" height="2" className="fill-gray-300" />

        {/* Zone overlays */}
        {/* Outside box area overlay (subtle) */}
        <rect x="2.5" y="2.5" width="95" height="65" rx="3.5" className="fill-indigo-50" />
        {/* Inside box overlay (more visible) */}
        <rect x="22" y="38" width="56" height="30" className="fill-emerald-50" />

        {/* Labels */}
        <foreignObject x="4" y="6" width="92" height="28">
          <div xmlns="http://www.w3.org/1999/xhtml" className="flex gap-2">
            <div className="flex-1 rounded-md border border-emerald-200 bg-white px-2 py-1">
              <div className="text-[10px] text-gray-600">Inside box</div>
              <div className="text-xs font-semibold text-gray-900">{inPct}% tentatives</div>
              <div className="text-[10px] text-gray-600">{cin}% conversion</div>
            </div>
            <div className="flex-1 rounded-md border border-indigo-200 bg-white px-2 py-1">
              <div className="text-[10px] text-gray-600">Outside box</div>
              <div className="text-xs font-semibold text-gray-900">{outPct}% tentatives</div>
              <div className="text-[10px] text-gray-600">{cout}% conversion</div>
            </div>
          </div>
        </foreignObject>

        {/* Little legend marker */}
        <text x="4" y="68" className="fill-gray-500" fontSize="3.2">
          Zones (agrégé) — pas de positions des tirs
        </text>
      </svg>
    </div>
  );
}