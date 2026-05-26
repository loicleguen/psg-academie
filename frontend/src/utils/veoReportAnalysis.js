const UNIT_LABELS = {
  count: '',
  '%': '%',
  minutes: 'min',
  seconds: 'sec',
};

export const VEO_TEAM_METRIC_LABELS = {
  team_possession_minutes: 'Possession (minutes)',
  team_possession_pct: 'Possession',
  team_possession_third_att_pct: 'Possession tiers offensif',
  team_possession_third_def_pct: 'Possession tiers defensif',
  team_possession_third_mid_pct: 'Possession tiers milieu',
  team_possession_won: 'Possessions gagnees',
  team_longest_sequence: 'Sequence la plus longue',
  team_passes_completed: 'Passes reussies',
  team_pass_zone_att_pct: 'Passes en zone offensive',
  team_pass_zone_mid_pct: 'Passes en zone milieu',
  team_pass_zone_def_pct: 'Passes en zone defensive',
  team_sequences_3_5: 'Sequences 3-5 passes',
  team_sequences_6_plus: 'Sequences 6+ passes',
  team_corners: 'Corners',
  team_free_kicks: 'Coups francs',
  team_throw_ins: 'Touches',
  team_total_attempts: 'Total tentatives',
  team_total_attempts_conceded: 'Total tentatives adverses',
  team_fouls: 'Fautes',
  team_fouls_conceded: 'Fautes adverses',
  team_penalties: 'Penalties',
  team_penalties_conceded: 'Penalties adverses',
  team_goals_scored: 'Buts marques',
  team_goals_conceded: 'Buts encaisses',
  team_shots: 'Tirs',
  team_shots_conceded: 'Tirs encaisses',
};

export const VEO_PLAYER_METRIC_LABELS = {
  player_goal_assists: 'Passes decisives',
  player_shots: 'Tirs',
  player_shots_on_target: 'Tirs cadres',
  player_goals: 'Buts',
  player_duels_won: 'Duels gagnes',
  player_fouls_committed: 'Fautes',
  player_cards: 'Cartons',
  player_offsides: 'Hors-jeu',
  player_dribbles_won: 'Dribbles reussis',
  player_tackles_won: 'Tacles reussis',
  player_recoveries: 'Recuperations',
  player_ball_losses: 'Pertes de balle',
};

export const VEO_HIDDEN_TEAM_METRIC_SLUGS = new Set(['team_goal_kicks']);

export const VEO_OPPONENT_ALIAS_BY_OWN_SLUG = {
  team_goals_scored: 'team_goals_conceded',
  team_shots: 'team_shots_conceded',
  team_total_attempts: 'team_total_attempts_conceded',
  team_fouls: 'team_fouls_conceded',
  team_penalties: 'team_penalties_conceded',
};

export const VEO_OWN_SLUG_BY_OPPONENT_ALIAS = Object.fromEntries(
  Object.entries(VEO_OPPONENT_ALIAS_BY_OWN_SLUG).map(([ownSlug, oppSlug]) => [oppSlug, ownSlug])
);

export const VEO_KPI_COMPARISON_ROWS = [
  { label: 'Buts', ownSlug: 'team_goals_scored', opponentSlug: 'team_goals_conceded' },
  { label: 'Tirs', ownSlug: 'team_shots', opponentSlug: 'team_shots_conceded' },
  { label: 'Possession', ownSlug: 'team_possession_pct', opponentFromOwnPct: true, unit: '%' },
  { label: 'Passes reussies', ownSlug: 'team_passes_completed' },
  { label: 'Corners', ownSlug: 'team_corners' },
  { label: 'Coups francs', ownSlug: 'team_free_kicks' },
  { label: 'Touches', ownSlug: 'team_throw_ins' },
];

export const VEO_CRITICAL_TEAM_METRICS = [
  { slug: 'team_goals_scored', side: 'OWN', label: 'Buts marques' },
  { slug: 'team_goals_conceded', side: 'OPPONENT', label: 'Buts encaisses' },
  { slug: 'team_shots', side: 'OWN', label: 'Tirs' },
  { slug: 'team_shots_conceded', side: 'OPPONENT', label: 'Tirs adverses' },
  { slug: 'team_possession_pct', side: 'OWN', label: 'Possession' },
  { slug: 'team_passes_completed', side: 'OWN', label: 'Passes reussies' },
];

export const VEO_REPORT_THRESHOLDS = {
  possessionPct: { good: 55, medium: 50, warning: 45 },
  passesCompleted: { good: 320, medium: 260, warning: 200 },
  shots: { good: 10, medium: 7, warning: 4 },
  goals: { good: 2, medium: 1 },
  corners: { good: 6, medium: 4, warning: 2 },
  globalScore: { good: 8, medium: 6, warning: 4 },
  passZoneAttackPct: { good: 20, medium: 15 },
  conversionPct: { good: 25, medium: 12 },
  goalsAgainst: { clean: 0, mediumMax: 1 },
  shotsAgainst: { bonusMax: 8 },
};

function normalizeNumeric(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isNaN(numeric) ? null : numeric;
}

function clampScore(value) {
  return Math.max(0, Math.min(10, Math.round(value)));
}

function getMetricFromMap(map, slug) {
  return map.get(slug) || null;
}

function getMetricValue(map, slug) {
  return getMetricFromMap(map, slug)?.value ?? null;
}

function formatMetricValue(value, unit) {
  if (value === null || value === undefined) {
    return '-';
  }
  const numericValue = Number(value);
  const displayValue = Number.isInteger(numericValue) ? String(numericValue) : numericValue.toFixed(1);
  const displayUnit = UNIT_LABELS[unit] ?? unit ?? '';
  return displayUnit ? `${displayValue} ${displayUnit}` : displayValue;
}

function formatTeamMetricLabel(metric) {
  return VEO_TEAM_METRIC_LABELS[metric.metric_slug] || metric.metric_label || metric.label || metric.metric_slug;
}

export function formatVeoMetricValue(value, unit) {
  return formatMetricValue(value, unit);
}

export function formatVeoTeamMetricLabel(metric) {
  return formatTeamMetricLabel(metric);
}

export function formatVeoPlayerMetricLabel(column) {
  return VEO_PLAYER_METRIC_LABELS[column.slug] || column.label || column.slug;
}

export function getVeoPerformanceTone(metricKey, rawValue) {
  const value = normalizeNumeric(rawValue);
  if (value === null) {
    return 'neutral';
  }

  if (metricKey === 'team_possession_pct') {
    if (value >= VEO_REPORT_THRESHOLDS.possessionPct.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.possessionPct.medium) return 'medium';
    if (value >= VEO_REPORT_THRESHOLDS.possessionPct.warning) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_passes_completed') {
    if (value >= VEO_REPORT_THRESHOLDS.passesCompleted.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.passesCompleted.medium) return 'medium';
    if (value >= VEO_REPORT_THRESHOLDS.passesCompleted.warning) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_shots') {
    if (value >= VEO_REPORT_THRESHOLDS.shots.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.shots.medium) return 'medium';
    if (value >= VEO_REPORT_THRESHOLDS.shots.warning) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_goals_scored') {
    if (value >= VEO_REPORT_THRESHOLDS.goals.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.goals.medium) return 'medium';
    return 'danger';
  }

  if (metricKey === 'team_corners') {
    if (value >= VEO_REPORT_THRESHOLDS.corners.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.corners.medium) return 'medium';
    if (value >= VEO_REPORT_THRESHOLDS.corners.warning) return 'warning';
    return 'danger';
  }

  if (metricKey === 'global_score') {
    if (value >= VEO_REPORT_THRESHOLDS.globalScore.good) return 'good';
    if (value >= VEO_REPORT_THRESHOLDS.globalScore.medium) return 'medium';
    if (value >= VEO_REPORT_THRESHOLDS.globalScore.warning) return 'warning';
    return 'danger';
  }

  return 'neutral';
}

function countExpectedTeamMetricCells(entrySchema) {
  const groups = entrySchema?.team_metrics_by_category ?? [];
  return groups.reduce(
    (total, group) =>
      total +
      (group.metrics ?? []).reduce((groupTotal, metric) => {
        if (VEO_HIDDEN_TEAM_METRIC_SLUGS.has(metric.slug)) {
          return groupTotal;
        }
        if (VEO_OWN_SLUG_BY_OPPONENT_ALIAS[metric.slug]) {
          return groupTotal;
        }
        if (metric.side === 'OPPONENT') {
          return groupTotal + 1;
        }
        return groupTotal + 2;
      }, 0),
    0
  );
}

function countCatalogPlayerMetrics(entrySchema) {
  const groups = entrySchema?.player_metrics_by_category ?? [];
  return groups.reduce((acc, group) => acc + (group.metrics?.length ?? 0), 0);
}

function getCatalogPlayerMetricSlugs(entrySchema) {
  const groups = entrySchema?.player_metrics_by_category ?? [];
  return new Set(
    groups.flatMap((group) => (group.metrics ?? []).map((metric) => metric.slug).filter(Boolean))
  );
}

function buildPresentPlayers(summary) {
  const allPlayers = summary?.player_metrics?.players ?? [];
  const playerNameById = new Map(
    allPlayers.map((player) => [Number(player.id), player.name || player.player_name])
  );

  if (!Array.isArray(summary?.participations)) {
    return allPlayers.map((player) => ({
      id: Number(player.id),
      name: player.name || player.player_name || `Joueur ${player.id}`,
    }));
  }

  const seen = new Set();
  return summary.participations
    .map((participation) => {
      const id = Number(participation.player_id ?? participation.id);
      if (!Number.isFinite(id) || seen.has(id)) {
        return null;
      }
      seen.add(id);
      return {
        id,
        name:
          participation.player_name ||
          participation.name ||
          playerNameById.get(id) ||
          `Joueur ${id}`,
      };
    })
    .filter(Boolean);
}

function buildQualityActions({ missingCritical, playersWithoutStats, inconsistencies }) {
  const actions = [];
  if (missingCritical.length > 0) {
    actions.push({
      key: 'missing-critical',
      tone: 'danger',
      label: `${missingCritical.length} indicateur(s) critique(s) manquant(s)`,
      detail: missingCritical.map((item) => item.label).join(', '),
      targetStep: 'IMPORT',
    });
  }
  if (playersWithoutStats.length > 0) {
    actions.push({
      key: 'players-without-stats',
      tone: 'warning',
      label: `${playersWithoutStats.length} joueur(s) present(s) sans metrique`,
      detail: playersWithoutStats.slice(0, 5).map((player) => player.name).join(', '),
      targetStep: 'VERIFY',
    });
  }
  if (inconsistencies.length > 0) {
    actions.push({
      key: 'inconsistencies',
      tone: 'warning',
      label: `${inconsistencies.length} coherence(s) a verifier`,
      detail: inconsistencies[0],
      targetStep: 'VERIFY',
    });
  }
  if (actions.length === 0) {
    actions.push({
      key: 'ready',
      tone: 'success',
      label: 'Donnees principales pretes',
      detail: 'Les indicateurs critiques sont renseignes et coherents.',
      targetStep: 'REPORT',
    });
  }
  return actions;
}

export function buildVeoReportAnalysis({ summary, entrySchema } = {}) {
  const ownMetrics = (summary?.team_metrics?.OWN ?? []).filter(
    (metric) => !VEO_HIDDEN_TEAM_METRIC_SLUGS.has(metric.metric_slug)
  );
  const opponentMetrics = (summary?.team_metrics?.OPPONENT ?? []).filter(
    (metric) => !VEO_HIDDEN_TEAM_METRIC_SLUGS.has(metric.metric_slug)
  );
  const ownMetricMap = new Map(ownMetrics.map((metric) => [metric.metric_slug, metric]));
  const opponentMetricMap = new Map(opponentMetrics.map((metric) => [metric.metric_slug, metric]));

  const possession = getMetricValue(ownMetricMap, 'team_possession_pct');
  const passes = getMetricValue(ownMetricMap, 'team_passes_completed');
  const shots = getMetricValue(ownMetricMap, 'team_shots');
  const shotsAgainst = getMetricValue(opponentMetricMap, 'team_shots_conceded');
  const goals = getMetricValue(ownMetricMap, 'team_goals_scored');
  const goalsAgainst = getMetricValue(opponentMetricMap, 'team_goals_conceded');
  const corners = getMetricValue(ownMetricMap, 'team_corners');
  const possessionOffThird = getMetricValue(ownMetricMap, 'team_possession_third_att_pct');
  const possessionMidThird = getMetricValue(ownMetricMap, 'team_possession_third_mid_pct');
  const passZoneAtt = getMetricValue(ownMetricMap, 'team_pass_zone_att_pct');
  const passZoneMid = getMetricValue(ownMetricMap, 'team_pass_zone_mid_pct');
  const opponentPossession = possession !== null ? Number((100 - possession).toFixed(1)) : null;
  const shotConversion = shots && shots > 0 && goals !== null ? (goals / shots) * 100 : null;
  const shotBalance = shots !== null && shotsAgainst !== null ? shots - shotsAgainst : null;

  const filledTeamKeys = new Set();
  ownMetrics.forEach((metric) => filledTeamKeys.add(`${metric.metric_slug}__OWN`));
  opponentMetrics.forEach((metric) => {
    const mappedSlug = VEO_OWN_SLUG_BY_OPPONENT_ALIAS[metric.metric_slug] || metric.metric_slug;
    filledTeamKeys.add(`${mappedSlug}__OPPONENT`);
  });

  const expectedTeamMetricCells = countExpectedTeamMetricCells(entrySchema);
  const catalogPlayerMetricsCount = countCatalogPlayerMetrics(entrySchema);
  const catalogPlayerMetricSlugs = getCatalogPlayerMetricSlugs(entrySchema);
  const valuesByPlayer = summary?.player_metrics?.values ?? {};
  const presentPlayers = buildPresentPlayers(summary);
  const presentPlayerIds = new Set(presentPlayers.map((player) => Number(player.id)));
  const playerMetricValuesFilled = presentPlayers.reduce((total, player) => {
    const rowValues = Object.entries(valuesByPlayer[String(player.id)] || {});
    return (
      total +
      rowValues.filter(([slug, value]) => {
        if (!catalogPlayerMetricSlugs.has(slug)) {
          return false;
        }
        return value !== null && value !== undefined;
      }).length
    );
  }, 0);
  const expectedPlayerMetricCells = presentPlayerIds.size * catalogPlayerMetricsCount;

  const teamCompletionPct =
    expectedTeamMetricCells > 0 ? (filledTeamKeys.size / expectedTeamMetricCells) * 100 : null;
  const playerCompletionPct =
    expectedPlayerMetricCells > 0 ? (playerMetricValuesFilled / expectedPlayerMetricCells) * 100 : null;

  const missingCritical = VEO_CRITICAL_TEAM_METRICS.filter((metric) => {
    const map = metric.side === 'OPPONENT' ? opponentMetricMap : ownMetricMap;
    return getMetricValue(map, metric.slug) === null;
  });

  const playersWithoutStats = presentPlayers.filter((player) => {
    const rowValues = Object.values(valuesByPlayer[String(player.id)] || {});
    return rowValues.filter((value) => value !== null && value !== undefined).length === 0;
  });

  const inconsistencies = [];
  const scoreFor = summary?.match?.score_for;
  const scoreAgainst = summary?.match?.score_against;
  if (goals !== null && scoreFor !== null && scoreFor !== undefined && Number(goals) !== Number(scoreFor)) {
    inconsistencies.push(`Buts VEO (${goals}) different du score (${scoreFor}).`);
  }
  if (
    goalsAgainst !== null &&
    scoreAgainst !== null &&
    scoreAgainst !== undefined &&
    Number(goalsAgainst) !== Number(scoreAgainst)
  ) {
    inconsistencies.push(`Buts encaisses VEO (${goalsAgainst}) different du score (${scoreAgainst}).`);
  }
  if (possession !== null && (Number(possession) < 0 || Number(possession) > 100)) {
    inconsistencies.push('La possession doit etre comprise entre 0 et 100%.');
  }
  const shotmapIn = getMetricValue(ownMetricMap, 'team_shotmap_attempts_inside_box_pct');
  const shotmapOut = getMetricValue(ownMetricMap, 'team_shotmap_attempts_outside_box_pct');
  if (shotmapIn !== null && shotmapOut !== null && Math.abs(Number(shotmapIn) + Number(shotmapOut) - 100) > 2) {
    inconsistencies.push('La repartition shotmap dans/hors surface ne totalise pas 100%.');
  }

  const comparisonRows = VEO_KPI_COMPARISON_ROWS.map((row) => {
    const ownMetric = row.ownSlug ? ownMetricMap.get(row.ownSlug) : null;
    const opponentMetric = row.opponentSlug
      ? opponentMetricMap.get(row.opponentSlug) || opponentMetricMap.get(row.ownSlug)
      : opponentMetricMap.get(row.ownSlug);
    const ownValue = ownMetric?.value ?? null;
    const opponentValue = row.opponentFromOwnPct ? opponentPossession : opponentMetric?.value ?? null;
    return {
      label: row.label,
      ownDisplay: formatMetricValue(ownValue, row.unit || ownMetric?.unit),
      opponentDisplay: formatMetricValue(opponentValue, row.unit || opponentMetric?.unit),
    };
  });

  const comparisonChartData = VEO_KPI_COMPARISON_ROWS.map((row) => {
    const ownMetric = row.ownSlug ? ownMetricMap.get(row.ownSlug) : null;
    const opponentMetric = row.opponentSlug
      ? opponentMetricMap.get(row.opponentSlug) || opponentMetricMap.get(row.ownSlug)
      : opponentMetricMap.get(row.ownSlug);
    const ownValue = ownMetric?.value ?? null;
    const opponentValue = row.opponentFromOwnPct ? opponentPossession : opponentMetric?.value ?? null;
    const ownNumber = ownValue === null ? 0 : Number(ownValue);
    const opponentNumber = opponentValue === null ? 0 : Number(opponentValue);
    return {
      label: row.label,
      ownValue: ownNumber,
      opponentValue: opponentNumber,
      maxValue: Math.max(ownNumber, opponentNumber, 1),
      unit: row.unit || ownMetric?.unit || opponentMetric?.unit || '',
    };
  });

  const ownPossessionAtt = Number(getMetricValue(ownMetricMap, 'team_possession_third_att_pct') ?? 0);
  const ownPossessionMid = Number(getMetricValue(ownMetricMap, 'team_possession_third_mid_pct') ?? 0);
  const ownPossessionDef = Number(getMetricValue(ownMetricMap, 'team_possession_third_def_pct') ?? 0);
  const territoryRows = [
    {
      label: 'Tiers offensif',
      ownPct: Math.round(ownPossessionAtt),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_possession_third_att_pct') ??
          Math.max(0, 100 - ownPossessionDef - ownPossessionMid)
      ),
    },
    {
      label: 'Tiers milieu',
      ownPct: Math.round(ownPossessionMid),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_possession_third_mid_pct') ??
          Math.max(0, 100 - ownPossessionAtt - ownPossessionDef)
      ),
    },
    {
      label: 'Tiers defensif',
      ownPct: Math.round(ownPossessionDef),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_possession_third_def_pct') ??
          Math.max(0, 100 - ownPossessionAtt - ownPossessionMid)
      ),
    },
  ];

  const ownPassAtt = Number(getMetricValue(ownMetricMap, 'team_pass_zone_att_pct') ?? 0);
  const ownPassMid = Number(getMetricValue(ownMetricMap, 'team_pass_zone_mid_pct') ?? 0);
  const ownPassDef = Number(getMetricValue(ownMetricMap, 'team_pass_zone_def_pct') ?? 0);
  const passZoneRows = [
    {
      label: 'Zone defensive',
      ownPct: Math.round(ownPassDef),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_pass_zone_def_pct') ?? Math.max(0, 100 - ownPassAtt - ownPassMid)
      ),
    },
    {
      label: 'Zone milieu',
      ownPct: Math.round(ownPassMid),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_pass_zone_mid_pct') ?? Math.max(0, 100 - ownPassAtt - ownPassDef)
      ),
    },
    {
      label: 'Zone offensive',
      ownPct: Math.round(ownPassAtt),
      oppPct: Math.round(
        getMetricValue(opponentMetricMap, 'team_pass_zone_att_pct') ?? Math.max(0, 100 - ownPassDef - ownPassMid)
      ),
    },
  ];

  const possessionScoreBase = possession === null ? 5 : possession >= 55 ? 7 : possession >= 50 ? 6 : 4;
  const progressionScoreBase = passZoneAtt === null ? 5 : passZoneAtt >= 20 ? 7 : passZoneAtt >= 15 ? 6 : 4;
  const finishingScoreBase = shotConversion === null ? 4 : shotConversion >= 25 ? 8 : shotConversion >= 12 ? 6 : 3;
  const defensiveScoreBase = goalsAgainst === null ? 5 : goalsAgainst === 0 ? 8 : goalsAgainst <= 1 ? 6 : 4;

  const possessionScore = clampScore(
    possessionScoreBase + (possessionOffThird !== null && possessionOffThird >= 20 ? 1 : 0)
  );
  const progressionScore = clampScore(progressionScoreBase + (passZoneMid !== null && passZoneMid <= 70 ? 1 : 0));
  const finishingScore = clampScore(finishingScoreBase + (shots !== null && shots >= 10 ? 1 : 0));
  const defensiveScore = clampScore(defensiveScoreBase + (shotsAgainst !== null && shotsAgainst <= 8 ? 1 : 0));
  const globalScore = clampScore((possessionScore + progressionScore + finishingScore + defensiveScore) / 4);

  const recommendations = [];
  if (finishingScore <= 5) {
    recommendations.push('Prioriser un cycle finition: enchainement controle-frappe dans la surface.');
  }
  if (progressionScore <= 5) {
    recommendations.push('Augmenter les circuits vers le dernier tiers (appui-remise + appel profondeur).');
  }
  if (defensiveScore <= 5) {
    recommendations.push('Travailler la protection axe + pressing a la perte sur 8-10 secondes.');
  }
  if (possessionScore <= 5) {
    recommendations.push('Renforcer la qualite de conservation sous pression (rondo directionnel).');
  }
  if (recommendations.length === 0) {
    recommendations.push('Conserver les principes actuels et augmenter le volume de situations de tir.');
  }

  const coachAnalysis = {
    globalScore,
    sections: [
      {
        title: 'Maitrise et occupation',
        score: possessionScore,
        bullets: [
          `Possession: ${formatMetricValue(possession, '%')} (adversaire ${formatMetricValue(opponentPossession, '%')}).`,
          `Occupation tiers offensif: ${formatMetricValue(possessionOffThird, '%')}.`,
          `Occupation tiers milieu: ${formatMetricValue(possessionMidThird, '%')}.`,
        ],
      },
      {
        title: 'Progression et creation',
        score: progressionScore,
        bullets: [
          `Passes reussies: ${formatMetricValue(passes, '')}.`,
          `Passes en zone offensive: ${formatMetricValue(passZoneAtt, '%')}.`,
          `Passes en zone milieu: ${formatMetricValue(passZoneMid, '%')}.`,
        ],
      },
      {
        title: 'Finition',
        score: finishingScore,
        bullets: [
          `Tirs: ${formatMetricValue(shots, '')}, buts: ${formatMetricValue(goals, '')}.`,
          `Conversion tirs/buts: ${formatMetricValue(shotConversion, '%')}.`,
          `Differentiel tirs: ${shotBalance === null ? '-' : shotBalance > 0 ? `+${shotBalance}` : shotBalance}.`,
        ],
      },
      {
        title: 'Solidite defensive',
        score: defensiveScore,
        bullets: [
          `Tirs encaisses: ${formatMetricValue(shotsAgainst, '')}.`,
          `Buts encaisses: ${formatMetricValue(goalsAgainst, '')}.`,
          `Corners obtenus: ${formatMetricValue(corners, '')}.`,
        ],
      },
    ],
    recommendations,
  };

  const reportKpis = [
    {
      label: 'Possession',
      value: possession !== null ? `${Number(possession).toFixed(1)}%` : '-',
      tone: getVeoPerformanceTone('team_possession_pct', possession),
    },
    {
      label: 'Passes',
      value: formatMetricValue(passes, ''),
      tone: getVeoPerformanceTone('team_passes_completed', passes),
    },
    {
      label: 'Tirs',
      value: formatMetricValue(shots, ''),
      tone: getVeoPerformanceTone('team_shots', shots),
    },
    {
      label: 'Buts',
      value: formatMetricValue(goals, ''),
      tone: getVeoPerformanceTone('team_goals_scored', goals),
    },
    {
      label: 'Corners',
      value: formatMetricValue(corners, ''),
      tone: getVeoPerformanceTone('team_corners', corners),
    },
  ];

  const visibleOwnMetrics = ownMetrics.slice(0, 8).map((metric) => ({
    label: formatTeamMetricLabel(metric),
    value: formatMetricValue(metric.value, metric.unit),
    tone: getVeoPerformanceTone(metric.metric_slug, metric.value),
  }));
  const visibleOpponentMetrics = opponentMetrics.slice(0, 8).map((metric) => ({
    label: formatTeamMetricLabel(metric),
    value: formatMetricValue(metric.value, metric.unit),
    tone: getVeoPerformanceTone(metric.metric_slug, metric.value),
  }));
  const qualityActions = buildQualityActions({ missingCritical, playersWithoutStats, inconsistencies });

  return {
    metrics: {
      possession,
      passes,
      shots,
      shotsAgainst,
      goals,
      goalsAgainst,
      corners,
      opponentPossession,
      shotConversion,
      shotBalance,
      possessionOffThird,
      possessionMidThird,
      passZoneAtt,
      passZoneMid,
    },
    quality: {
      teamMetricsFilled: filledTeamKeys.size,
      expectedTeamMetricCells,
      teamCompletionPct,
      catalogPlayerMetricsCount,
      playerMetricValuesFilled,
      expectedPlayerMetricCells,
      playerCompletionPct,
      missingCritical,
      playersWithoutStats,
      inconsistencies,
      actions: qualityActions,
    },
    presentPlayers,
    presentPlayerIds,
    ownMetrics,
    opponentMetrics,
    ownMetricMap,
    opponentMetricMap,
    comparisonRows,
    comparisonChartData,
    territoryRows,
    passZoneRows,
    coachAnalysis,
    reportKpis,
    visibleOwnMetrics,
    visibleOpponentMetrics,
    playersTracked: presentPlayers.length,
  };
}
