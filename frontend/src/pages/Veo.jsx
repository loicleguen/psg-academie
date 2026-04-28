import { useEffect, useMemo, useRef, useState } from 'react';
import { TrashIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import ShotmapOverview from "../components/veo/ShotmapOverview";
import SmartPastePanel from '../components/veo/SmartPastePanel';
import StatsBarsPanel from "../components/veo/StatsBarsPanel";
import { catapultService } from '../services/catapultService';
import { veoService } from '../services/veoService';
import { buildVeoReportAnalysis } from '../utils/veoReportAnalysis';

const MATCH_TYPES = ['LEAGUE', 'CUP', 'FRIENDLY', 'TOURNAMENT'];

const VEO_WORKFLOW_STEPS = [
  { key: 'SESSION', label: 'Session', helper: 'Creer ou choisir le match' },
  { key: 'IMPORT', label: 'Importer VEO', helper: 'Coller les donnees et remplir' },
  { key: 'VERIFY', label: 'Verifier donnees', helper: 'Controler qualite et joueurs' },
  { key: 'REPORT', label: 'Voir rapport', helper: 'Lire et ouvrir le rendu' },
];

const EMPTY_MATCH_FORM = {
  date: '',
  team_name: '',
  opponent_name: '',
  is_home: true,
  match_type: 'LEAGUE',
  competition: '',
  score_for: '',
  score_against: '',
  veo_title: '',
  veo_url: '',
  veo_duration: '',
  veo_camera: '',
};

const ESSENTIAL_TEAM_METRICS = new Set([
  'team_possession_pct',
  'team_passes_completed',
  'team_goals_scored',
  'team_goals_conceded',
  'team_shots',
  'team_shots_conceded',
  'team_corners',
  'team_free_kicks',
  'team_throw_ins',
]);

const ESSENTIAL_PLAYER_METRICS = new Set([
  'player_goal_assists',
  'player_shots',
  'player_shots_on_target',
  'player_goals',
  'player_duels_won',
  'player_fouls_committed',
  'player_cards',
  'player_offsides',
  'player_dribbles_won',
  'player_tackles_won',
  'player_recoveries',
  'player_ball_losses',
]);

const PLAYER_METRIC_DISPLAY_ORDER = [
  'player_goal_assists',
  'player_shots',
  'player_shots_on_target',
  'player_goals',
  'player_duels_won',
  'player_fouls_committed',
  'player_cards',
  'player_offsides',
  'player_dribbles_won',
  'player_tackles_won',
  'player_recoveries',
  'player_ball_losses',
];

const PLAYER_METRIC_ORDER_INDEX = new Map(
  PLAYER_METRIC_DISPLAY_ORDER.map((slug, index) => [slug, index])
);

const METRIC_LABEL_OVERRIDES = {
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

const PLAYER_METRIC_MAX_VALUES = {
  player_cards: 3,
};

const PLAYER_METRIC_AUTO_ZERO_LABELS = {
  player_goal_assists: 'Equipe sans but',
  player_goals: 'Equipe sans but',
  player_shots: 'Equipe sans tir',
  player_shots_on_target: 'Equipe sans tir',
  player_fouls_committed: 'Equipe sans faute',
};

const UNIT_LABELS = {
  count: '',
  '%': '%',
  minutes: 'min',
  seconds: 'sec',
};

const OPPONENT_ALIAS_BY_OWN_SLUG = {
  team_goals_scored: 'team_goals_conceded',
  team_shots: 'team_shots_conceded',
  team_total_attempts: "team_total_attempts_conceded",
  team_fouls: "team_fouls_conceded",
  team_penalties: "team_penalties_conceded",
};

const HIDDEN_TEAM_METRIC_SLUGS = new Set([
  ...Object.values(OPPONENT_ALIAS_BY_OWN_SLUG),
  'team_goal_kicks',
]);

const FORM_CONTROL_CLASS =
  'mt-1 w-full h-10 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500';

const makeTeamMetricKey = (slug, side) => `${slug}__${side}`;
const makePlayerMetricKey = (playerId, slug) => `${playerId}__${slug}`;

function toNumberOrNull(value, parser = parseFloat) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const parsed = parser(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function toInputStringOrEmpty(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value);
}

function formatMatchLabel(match) {
  return `${match.date} - ${match.opponent_name} (${match.score_for ?? 0}-${match.score_against ?? 0})`;
}

function inferOpponentFromSessionTitle(sessionTitle) {
  const title = (sessionTitle || '').trim();
  if (!title) {
    return '';
  }

  const headerPart = title.split('/')[0]?.trim() || title;
  if (!/^MATCH\b/i.test(headerPart)) {
    return '';
  }

  const withoutPrefix = headerPart.replace(/^MATCH\s+/i, '').trim();
  return withoutPrefix || '';
}

function normalizeNameForMatching(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function normalizePlayerNameForStorage(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLocaleUpperCase('fr-FR');
}

function buildTokenSignature(value) {
  const normalized = normalizeNameForMatching(value);
  if (!normalized) {
    return '';
  }
  return normalized
    .split(' ')
    .filter(Boolean)
    .sort()
    .join(' ');
}

function buildVeoPlayerMatchKeys(player) {
  const first = normalizeNameForMatching(player.first_name);
  const last = normalizeNameForMatching(player.last_name);
  const full = normalizeNameForMatching(`${player.first_name} ${player.last_name}`);
  const reverse = normalizeNameForMatching(`${player.last_name} ${player.first_name}`);
  const signature = buildTokenSignature(`${player.first_name} ${player.last_name}`);

  return new Set([first, last, full, reverse, signature].filter(Boolean));
}

function splitPlayerNameForVeo(name) {
  const cleaned = String(name || '')
    .trim()
    .replace(/\s+/g, ' ');
  if (!cleaned) {
    return null;
  }

  const tokens = cleaned.split(' ');
  if (tokens.length === 1) {
    const normalized = normalizePlayerNameForStorage(tokens[0]);
    return {
      firstName: normalized,
      lastName: normalized,
    };
  }

  return {
    firstName: normalizePlayerNameForStorage(tokens[0]),
    lastName: normalizePlayerNameForStorage(tokens.slice(1).join(' ')),
  };
}

function formatPlayerDisplayName(player) {
  const firstName = normalizePlayerNameForStorage(player?.first_name);
  const lastName = normalizePlayerNameForStorage(player?.last_name);
  return `${firstName} ${lastName}`.trim();
}

function getParticipationMinutesValue(state) {
  const minutes = Number(state?.minutes_played);
  return Number.isFinite(minutes) ? minutes : 0;
}

function getParticipationRoleLabel(state) {
  if (state?.is_starter) {
    return 'Titulaire';
  }
  return getParticipationMinutesValue(state) > 0 ? 'Entré en jeu' : 'Présent';
}

function getNumericInputValue(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function getMetricDisplayLabel(metric) {
  return METRIC_LABEL_OVERRIDES[metric.slug] || metric.label_fr;
}

function getMetricMetaLabel(metric, options = {}) {
  const { showSide = true } = options;
  const parts = [];
  if (showSide && metric.side === 'OPPONENT') {
    parts.push('Adversaire');
  }

  const normalizedUnit = UNIT_LABELS[metric.unit] ?? metric.unit;
  if (normalizedUnit) {
    parts.push(normalizedUnit);
  }

  return parts.join(' • ');
}

function buildTeamMetricFieldConfigs(metric) {
  const side = metric.side || 'OWN';

  if (HIDDEN_TEAM_METRIC_SLUGS.has(metric.slug)) {
    return [];
  }

  if (side === 'OPPONENT') {
    return [
      {
        metric,
        inputSlug: metric.slug,
        inputSide: 'OPPONENT',
        saveSlug: metric.slug,
      },
    ];
  }

  return [
    {
      metric,
      inputSlug: metric.slug,
      inputSide: 'OWN',
      saveSlug: metric.slug,
    },
    {
      metric,
      inputSlug: metric.slug,
      inputSide: 'OPPONENT',
      saveSlug: OPPONENT_ALIAS_BY_OWN_SLUG[metric.slug] || metric.slug,
    },
  ];
}

export default function Veo() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingMatchId, setDeletingMatchId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [players, setPlayers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [entrySchema, setEntrySchema] = useState(null);

  const [selectedMatchId, setSelectedMatchId] = useState('');
  const [summary, setSummary] = useState(null);
  const [matchForm, setMatchForm] = useState(EMPTY_MATCH_FORM);
  const [activeWorkflowStep, setActiveWorkflowStep] = useState('SESSION');

  const [participationState, setParticipationState] = useState({});
  const [teamMetricInputs, setTeamMetricInputs] = useState({});
  const [playerMetricInputs, setPlayerMetricInputs] = useState({});
  const [catapultSessions, setCatapultSessions] = useState([]);
  const [catapultTeams, setCatapultTeams] = useState([]);
  const [selectedCatapultSessionTitle, setSelectedCatapultSessionTitle] = useState('');
  const [teamMetricsView, setTeamMetricsView] = useState("BARS");
  const [teamMetricsMenu, setTeamMetricsMenu] = useState('OWN');
  const [rosterSyncMessage, setRosterSyncMessage] = useState('');
  const [smartPasteParsed, setSmartPasteParsed] = useState(null);
  const latestSelectedMatchRequest = useRef(0);

  const teamMetricsByCategory = useMemo(
    () => entrySchema?.team_metrics_by_category ?? [],
    [entrySchema]
  );
  const playerMetricsByCategory = useMemo(
    () => entrySchema?.player_metrics_by_category ?? [],
    [entrySchema]
  );

  const persistedShotmapParsed = useMemo(() => {
    const getOwn = (slug) => teamMetricInputs?.[`${slug}__OWN`];

    const conv = getOwn("team_shotmap_conversion_rate_pct");
    const convIn = getOwn("team_shotmap_inside_box_conversion_rate_pct");
    const convOut = getOwn("team_shotmap_outside_box_conversion_rate_pct");
    const attIn = getOwn("team_shotmap_attempts_inside_box_pct");
    const attOut = getOwn("team_shotmap_attempts_outside_box_pct");

    const goals = getOwn("team_goals_scored");
    const shots = getOwn("team_shots");
    const totalAttempts = getOwn("team_total_attempts");

    const hasAnything =
      [conv, convIn, convOut, attIn, attOut, goals, shots, totalAttempts].some(
        (v) => v !== null && v !== undefined && v !== ""
      );

    if (!hasAnything) return null;

    return {
      type: "carte_des_tirs",
      data: {
        type: "carte_des_tirs",
        data: {
          Buts: goals ?? "",
          Tirs: shots ?? "",
          "Total des tentatives": totalAttempts ?? "",
          team_shotmap_conversion_rate_pct: conv ?? "",
          team_shotmap_inside_box_conversion_rate_pct: convIn ?? "",
          team_shotmap_outside_box_conversion_rate_pct: convOut ?? "",
          team_shotmap_attempts_inside_box_pct: attIn ?? "",
          team_shotmap_attempts_outside_box_pct: attOut ?? "",
        },
      },
    };
  }, [teamMetricInputs]);

  const shotmapToDisplay =
    smartPasteParsed?.type === "carte_des_tirs"
    ? smartPasteParsed
    : persistedShotmapParsed;

  const visiblePlayerMetricsByCategory = useMemo(() => {
    return playerMetricsByCategory
      .map((group) => ({
        ...group,
        metrics: group.metrics.filter((metric) => ESSENTIAL_PLAYER_METRICS.has(metric.slug)),
      }))
      .filter((group) => group.metrics.length > 0);
  }, [playerMetricsByCategory]);

  const allTeamMetricFields = useMemo(
    () =>
      teamMetricsByCategory.flatMap((group) =>
        group.metrics.flatMap((metric) => buildTeamMetricFieldConfigs(metric))
      ),
    [teamMetricsByCategory]
  );

  const allTeamMetricFieldsByCategory = useMemo(
    () =>
      teamMetricsByCategory
        .map((group) => ({
          ...group,
          fields: group.metrics.flatMap((metric) =>
            buildTeamMetricFieldConfigs(metric)
          ),
        }))
        .filter((group) => group.fields.length > 0),
    [teamMetricsByCategory]
  );

  const allFlatPlayerMetrics = useMemo(
    () => playerMetricsByCategory.flatMap((group) => group.metrics),
    [playerMetricsByCategory]
  );

  const teamMetricFieldByInputKey = useMemo(() => {
    const index = new Map();
    allTeamMetricFields.forEach((field) => {
      index.set(makeTeamMetricKey(field.inputSlug, field.inputSide), field);
    });
    return index;
  }, [allTeamMetricFields]);

  const ownTeamMetricValueBySlug = useMemo(() => {
    const values = {};
    (summary?.team_metrics?.OWN ?? []).forEach((metric) => {
      values[metric.metric_slug] = metric.value;
    });
    Object.entries(teamMetricInputs).forEach(([key, raw]) => {
      const field = teamMetricFieldByInputKey.get(key);
      if (!field || field.inputSide !== 'OWN') {
        return;
      }
      const numeric = getNumericInputValue(raw);
      if (numeric !== null) {
        values[field.saveSlug] = numeric;
      }
    });
    return values;
  }, [summary, teamMetricInputs, teamMetricFieldByInputKey]);

  const knownPlayerMetricSlugs = useMemo(
    () => new Set(allFlatPlayerMetrics.map((metric) => metric.slug)),
    [allFlatPlayerMetrics]
  );

  const visibleFlatPlayerMetrics = useMemo(
    () =>
      visiblePlayerMetricsByCategory
        .flatMap((group) => group.metrics)
        .sort((left, right) => {
          const leftIndex = PLAYER_METRIC_ORDER_INDEX.get(left.slug) ?? Number.MAX_SAFE_INTEGER;
          const rightIndex = PLAYER_METRIC_ORDER_INDEX.get(right.slug) ?? Number.MAX_SAFE_INTEGER;
          if (leftIndex !== rightIndex) {
            return leftIndex - rightIndex;
          }
          return left.slug.localeCompare(right.slug);
        }),
    [visiblePlayerMetricsByCategory]
  );

  const playersForMetricsGrid = useMemo(
    () => {
      const selectedPlayers = players.filter((player) => participationState[player.id]?.selected);
      return selectedPlayers.sort((left, right) => {
        const leftState = participationState[left.id] || {};
        const rightState = participationState[right.id] || {};
        const leftMinutes = getParticipationMinutesValue(leftState);
        const rightMinutes = getParticipationMinutesValue(rightState);
        if (leftMinutes !== rightMinutes) {
          return rightMinutes - leftMinutes;
        }
        if (!!leftState.is_starter !== !!rightState.is_starter) {
          return leftState.is_starter ? -1 : 1;
        }
        const leftName = `${left.last_name || ''} ${left.first_name || ''}`.trim();
        const rightName = `${right.last_name || ''} ${right.first_name || ''}`.trim();
        return leftName.localeCompare(rightName, 'fr', { sensitivity: 'base' });
      });
    },
    [players, participationState]
  );

  const autoZeroPlayerMetricReasons = useMemo(() => {
    const reasons = {};
    const scoreFor = getNumericInputValue(summary?.match?.score_for ?? matchForm.score_for);
    const shots = getNumericInputValue(ownTeamMetricValueBySlug.team_shots);
    const fouls = getNumericInputValue(ownTeamMetricValueBySlug.team_fouls);

    if (scoreFor === 0) {
      reasons.player_goals = PLAYER_METRIC_AUTO_ZERO_LABELS.player_goals;
      reasons.player_goal_assists = PLAYER_METRIC_AUTO_ZERO_LABELS.player_goal_assists;
    }
    if (shots === 0) {
      reasons.player_shots = PLAYER_METRIC_AUTO_ZERO_LABELS.player_shots;
      reasons.player_shots_on_target = PLAYER_METRIC_AUTO_ZERO_LABELS.player_shots_on_target;
    }
    if (fouls === 0) {
      reasons.player_fouls_committed = PLAYER_METRIC_AUTO_ZERO_LABELS.player_fouls_committed;
    }

    return reasons;
  }, [summary, matchForm.score_for, ownTeamMetricValueBySlug]);

  const getDisplayedPlayerMetricInputValue = (playerId, metricSlug, hasMinutes = true) => {
    if (!hasMinutes || autoZeroPlayerMetricReasons[metricSlug]) {
      return '0';
    }
    return playerMetricInputs[makePlayerMetricKey(playerId, metricSlug)] ?? '0';
  };

  const playerMetricValidation = useMemo(() => {
    const errors = [];
    const warnings = [];
    const totals = {};
    const scoreFor = getNumericInputValue(summary?.match?.score_for ?? matchForm.score_for);
    const teamShots = getNumericInputValue(ownTeamMetricValueBySlug.team_shots);

    playersForMetricsGrid.forEach((player) => {
      const state = participationState[player.id] || {};
      const hasMinutes = getParticipationMinutesValue(state) > 0;
      visibleFlatPlayerMetrics.forEach((metric) => {
        const raw = !hasMinutes || autoZeroPlayerMetricReasons[metric.slug]
          ? '0'
          : playerMetricInputs[makePlayerMetricKey(player.id, metric.slug)] ?? '0';
        const value = getNumericInputValue(raw) ?? 0;
        const playerName = formatPlayerDisplayName(player);
        totals[metric.slug] = (totals[metric.slug] || 0) + value;

        if (value < 0) {
          errors.push(`${playerName}: ${getMetricDisplayLabel(metric)} ne peut pas etre negatif.`);
        }

        const maxValue = PLAYER_METRIC_MAX_VALUES[metric.slug];
        if (maxValue !== undefined && value > maxValue) {
          errors.push(`${playerName}: ${getMetricDisplayLabel(metric)} ne peut pas depasser ${maxValue}.`);
        }
      });

      const shots =
        getNumericInputValue(
          !hasMinutes || autoZeroPlayerMetricReasons.player_shots
            ? '0'
            : playerMetricInputs[makePlayerMetricKey(player.id, 'player_shots')] ?? '0'
        ) ?? 0;
      const shotsOnTarget =
        getNumericInputValue(
          !hasMinutes || autoZeroPlayerMetricReasons.player_shots_on_target
            ? '0'
            : playerMetricInputs[makePlayerMetricKey(player.id, 'player_shots_on_target')] ?? '0'
        ) ?? 0;
      if (shotsOnTarget > shots) {
        errors.push(`${formatPlayerDisplayName(player)}: tirs cadres superieurs aux tirs.`);
      }
    });

    if (scoreFor !== null) {
      const totalGoals = totals.player_goals || 0;
      const totalAssists = totals.player_goal_assists || 0;
      if (totalGoals > scoreFor) {
        errors.push(`Total buts joueurs (${totalGoals}) superieur au score equipe (${scoreFor}).`);
      }
      if (totalAssists > scoreFor) {
        warnings.push(`Total passes decisives (${totalAssists}) superieur au nombre de buts equipe (${scoreFor}).`);
      }
    }

    if (teamShots !== null && (totals.player_shots || 0) > teamShots) {
      warnings.push(`Total tirs joueurs (${totals.player_shots || 0}) superieur aux tirs equipe (${teamShots}).`);
    }

    return { errors, warnings, totals };
  }, [
    playersForMetricsGrid,
    participationState,
    visibleFlatPlayerMetrics,
    playerMetricInputs,
    autoZeroPlayerMetricReasons,
    summary,
    matchForm.score_for,
    ownTeamMetricValueBySlug,
  ]);

  const selectedCatapultSession = useMemo(
    () =>
      catapultSessions.find((session) => session.session_title === selectedCatapultSessionTitle) || null,
    [catapultSessions, selectedCatapultSessionTitle]
  );

  const catapultSessionsForDate = useMemo(() => {
    if (!matchForm.date) {
      return [];
    }
    return catapultSessions.filter((session) => session.date === matchForm.date);
  }, [catapultSessions, matchForm.date]);

  const metricCatalogStats = useMemo(() => {
    const teamByCategory = teamMetricsByCategory.map((group) => ({
      category: group.category_label_fr,
      count: group.metrics.filter((metric) => !HIDDEN_TEAM_METRIC_SLUGS.has(metric.slug)).length,
    }));
    const playerByCategory = playerMetricsByCategory.map((group) => ({
      category: group.category_label_fr,
      count: group.metrics.length,
    }));

    return {
      totalTeam: teamByCategory.reduce((acc, group) => acc + group.count, 0),
      totalPlayer: allFlatPlayerMetrics.length,
      teamByCategory,
      playerByCategory,
    };
  }, [teamMetricsByCategory, playerMetricsByCategory, allFlatPlayerMetrics]);

  const veoReportAnalysis = useMemo(
    () => buildVeoReportAnalysis({ summary, entrySchema }),
    [summary, entrySchema]
  );
  const veoQuality = veoReportAnalysis.quality;
  const selectedSessionReportPath = selectedCatapultSessionTitle
    ? `/catapult/sessions/${encodeURIComponent(selectedCatapultSessionTitle)}`
    : '';

  const setFlash = (message, type = 'success') => {
    if (type === 'success') {
      setSuccess(message);
      setError('');
    } else {
      setError(message);
      setSuccess('');
    }
  };

  const resetSelectedMatchState = () => {
    setSummary(null);
    setPlayers([]);
    setParticipationState({});
    setTeamMetricInputs({});
    setPlayerMetricInputs({});
    setRosterSyncMessage('');
  };

  const refreshCatapultData = async () => {
    try {
      const [sessionsData, teamsData] = await Promise.all([
        catapultService.getSessions(),
        catapultService.getTeams(),
      ]);

      const normalizedSessions = Array.isArray(sessionsData) ? sessionsData : [];
      const normalizedTeams = Array.isArray(teamsData) ? teamsData : [];

      if (!Array.isArray(sessionsData) || !Array.isArray(teamsData)) {
        console.error('Format inattendu depuis Catapult API', {
          sessionsData,
          teamsData,
        });
      }

      setCatapultSessions(normalizedSessions);
      setCatapultTeams(normalizedTeams);

      if (normalizedSessions.length > 0) {
        if (!matchForm.date) {
          setMatchForm((prev) => ({ ...prev, date: normalizedSessions[0].date }));
        }
        if (!selectedCatapultSessionTitle) {
          setSelectedCatapultSessionTitle(normalizedSessions[0].session_title);
        }
      }
    } catch (err) {
      console.error('Erreur chargement sessions Catapult pour bootstrap VEO:', err);
      setCatapultSessions([]);
      setCatapultTeams([]);
    }
  };

  const refreshMatches = async (preferredMatchId = null) => {
    const matchesData = await veoService.getMatches();
    const normalizedMatches = Array.isArray(matchesData) ? matchesData : [];
    if (!Array.isArray(matchesData)) {
      console.error('Format inattendu depuis Veo API /matches:', matchesData);
    }
    setMatches(normalizedMatches);

    if (preferredMatchId) {
      setSelectedMatchId(String(preferredMatchId));
      return normalizedMatches;
    }

    if (!selectedMatchId && normalizedMatches.length > 0) {
      setSelectedMatchId(String(normalizedMatches[0].id));
    }

    return normalizedMatches;
  };

  const loadVeoBootstrap = async () => {
    try {
      setLoading(true);
      setError('');
      const [entrySchemaData] = await Promise.all([veoService.getEntrySchema(false)]);
      setEntrySchema(entrySchemaData);
      await Promise.all([refreshMatches(), refreshCatapultData()]);
    } catch (err) {
      console.error(err);
      setFlash('Erreur lors du chargement des donnees Veo', 'error');
    } finally {
      setLoading(false);
    }
  };

  const alignPlayersWithCatapultRoster = async (matchSummary, teamName, initialPlayers) => {
    const cleanTeamName = (teamName || '').trim();
    if (!cleanTeamName) {
      return { players: initialPlayers, message: '' };
    }

    let catapultRoster = [];
    try {
      const rosterData = await catapultService.getTeamPlayers(cleanTeamName);
      catapultRoster = Array.isArray(rosterData) ? rosterData : [];
      if (!Array.isArray(rosterData)) {
        console.error('Format inattendu depuis Catapult API /teams/{team}/players:', rosterData);
      }
    } catch (err) {
      console.error('Impossible de charger le roster Catapult pour alignement VEO:', err);
      return { players: initialPlayers, message: '' };
    }

    const rosterNames = catapultRoster
      .map((player) => player?.player_name || player?.full_name || '')
      .map((name) => String(name).trim())
      .filter(Boolean);

    if (rosterNames.length === 0) {
      return { players: initialPlayers, message: '' };
    }

    const buildPlayerIndex = (list) => {
      const index = new Map();
      list.forEach((player) => {
        buildVeoPlayerMatchKeys(player).forEach((key) => {
          if (!index.has(key)) {
            index.set(key, player);
          }
        });
      });
      return index;
    };

    const resolveRosterName = (index, name) => {
      const direct = normalizeNameForMatching(name);
      const signature = buildTokenSignature(name);
      return index.get(direct) || index.get(signature) || null;
    };

    let mergedPlayers = initialPlayers;
    let playerIndex = buildPlayerIndex(mergedPlayers);
    let createdPlayers = 0;
    let normalizedPlayersCount = 0;
    let shouldRefreshPlayers = false;

    const missingNames = rosterNames.filter((name) => !resolveRosterName(playerIndex, name));
    for (const missingName of missingNames) {
      const split = splitPlayerNameForVeo(missingName);
      if (!split) {
        continue;
      }

      try {
        await veoService.createPlayer({
          team_id: matchSummary.match.team_id,
          first_name: split.firstName,
          last_name: split.lastName,
          main_position: 'INCONNU',
          secondary_positions: null,
        });
        createdPlayers += 1;
        shouldRefreshPlayers = true;
      } catch (err) {
        console.error('Creation joueur VEO impossible pendant sync roster:', missingName, err);
      }
    }

    for (const player of mergedPlayers) {
      const normalizedFirst = normalizePlayerNameForStorage(player.first_name);
      const normalizedLast = normalizePlayerNameForStorage(player.last_name);
      const firstDiffers = String(player.first_name || '').trim() !== normalizedFirst;
      const lastDiffers = String(player.last_name || '').trim() !== normalizedLast;
      if (!firstDiffers && !lastDiffers) {
        continue;
      }

      try {
        await veoService.updatePlayer(player.id, {
          first_name: normalizedFirst,
          last_name: normalizedLast,
        });
        normalizedPlayersCount += 1;
        shouldRefreshPlayers = true;
      } catch (err) {
        console.error('Normalisation nom joueur VEO impossible:', player.id, err);
      }
    }

    if (shouldRefreshPlayers) {
      const refreshedPlayers = await veoService.getPlayers(matchSummary.match.team_id);
      if (Array.isArray(refreshedPlayers)) {
        mergedPlayers = refreshedPlayers;
        playerIndex = buildPlayerIndex(mergedPlayers);
      }
    }

    const rosterOrderByPlayerId = new Map();
    rosterNames.forEach((name, index) => {
      const matchedPlayer = resolveRosterName(playerIndex, name);
      if (matchedPlayer && !rosterOrderByPlayerId.has(matchedPlayer.id)) {
        rosterOrderByPlayerId.set(matchedPlayer.id, index);
      }
    });

    const participationIds = new Set(
      (matchSummary.participations || []).map((participation) => Number(participation.player_id))
    );

    const orderedPlayers = [...mergedPlayers].sort((left, right) => {
      const leftOrder = rosterOrderByPlayerId.get(left.id);
      const rightOrder = rosterOrderByPlayerId.get(right.id);
      const leftHasRoster = leftOrder !== undefined;
      const rightHasRoster = rightOrder !== undefined;

      if (leftHasRoster && rightHasRoster && leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }
      if (leftHasRoster !== rightHasRoster) {
        return leftHasRoster ? -1 : 1;
      }

      const leftSelected = participationIds.has(Number(left.id));
      const rightSelected = participationIds.has(Number(right.id));
      if (leftSelected !== rightSelected) {
        return leftSelected ? -1 : 1;
      }

      const leftName = `${left.last_name || ''} ${left.first_name || ''}`.trim();
      const rightName = `${right.last_name || ''} ${right.first_name || ''}`.trim();
      return leftName.localeCompare(rightName, 'fr', { sensitivity: 'base' });
    });

    const unresolvedCount = rosterNames.filter((name) => !resolveRosterName(playerIndex, name)).length;
    const messageParts = [];
    if (createdPlayers > 0) {
      messageParts.push(`${createdPlayers} joueur(s) ajouté(s) à VEO depuis le roster Catapult`);
    }
    if (normalizedPlayersCount > 0) {
      messageParts.push(`${normalizedPlayersCount} joueur(s) normalisé(s) en MAJ`);
    }
    if (unresolvedCount > 0) {
      messageParts.push(`${unresolvedCount} nom(s) non aligné(s) automatiquement`);
    }

    return {
      players: orderedPlayers,
      message: messageParts.join(' • '),
    };
  };

  const initializeMatchForms = async (matchSummary, teamName = '') => {
    const teamPlayers = await veoService.getPlayers(matchSummary.match.team_id);
    let normalizedPlayers = Array.isArray(teamPlayers) ? teamPlayers : [];
    if (!Array.isArray(teamPlayers)) {
      console.error('Format inattendu depuis Veo API /players:', teamPlayers);
    }

    const aligned = await alignPlayersWithCatapultRoster(matchSummary, teamName, normalizedPlayers);
    normalizedPlayers = aligned.players;
    setRosterSyncMessage(aligned.message);

    setPlayers(normalizedPlayers);

    const nextParticipationState = {};
    normalizedPlayers.forEach((player) => {
      nextParticipationState[player.id] = {
        selected: false,
        is_starter: false,
        is_captain: false,
        minutes_played: '',
        position_played: player.main_position || '',
      };
    });

    matchSummary.participations.forEach((part) => {
      nextParticipationState[part.player_id] = {
        selected: true,
        is_starter: !!part.is_starter,
        is_captain: !!part.is_captain,
        minutes_played:
          part.minutes_played === null || part.minutes_played === undefined
            ? ''
            : String(part.minutes_played),
        position_played: part.position_played || part.main_position || '',
      };
    });
    setParticipationState(nextParticipationState);

    const nextTeamInputs = {};
    allTeamMetricFields.forEach((field) => {
      const row = matchSummary.team_metrics?.[field.inputSide]?.find(
        (item) => item.metric_slug === field.saveSlug
      );
      if (row && row.value !== null && row.value !== undefined) {
        nextTeamInputs[makeTeamMetricKey(field.inputSlug, field.inputSide)] = String(row.value);
      }
    });
    setTeamMetricInputs(nextTeamInputs);

    const nextPlayerInputs = {};
    const gridValues = matchSummary.player_metrics?.values ?? {};
    Object.entries(gridValues).forEach(([playerId, metricsMap]) => {
      Object.entries(metricsMap).forEach(([metricSlug, value]) => {
        if (value !== null && value !== undefined) {
          nextPlayerInputs[makePlayerMetricKey(playerId, metricSlug)] = String(value);
        }
      });
    });
    setPlayerMetricInputs(nextPlayerInputs);
  };

  const loadSelectedMatch = async (matchId) => {
    if (!matchId) {
      resetSelectedMatchState();
      return;
    }

    const requestId = latestSelectedMatchRequest.current + 1;
    latestSelectedMatchRequest.current = requestId;

    try {
      setSaving(true);
      const matchSummary = await veoService.getMatchSummary(Number(matchId));
      if (latestSelectedMatchRequest.current !== requestId) {
        return;
      }
      setSummary(matchSummary);
      const matchDate = String(matchSummary.match.date).slice(0, 10);
      const sessionsSameDate = catapultSessions.filter((session) => session.date === matchDate);
      const normalizedVeoTitle = (matchSummary.match.veo_title || '').trim().toLowerCase();
      const linkedSession =
        sessionsSameDate.find(
          (session) => (session.session_title || '').trim().toLowerCase() === normalizedVeoTitle
        ) || sessionsSameDate[0] || null;
      const linkedCatapultTeam = linkedSession
        ? catapultTeams.find((team) => Number(team.id) === Number(linkedSession.team_id))
        : null;
      const resolvedTeamName = linkedCatapultTeam?.name || '';

      setSelectedCatapultSessionTitle(linkedSession?.session_title || '');
      setMatchForm((prev) => ({
        ...prev,
        date: matchDate,
        team_name: resolvedTeamName || prev.team_name,
        opponent_name: matchSummary.match.opponent_name || '',
        is_home: !!matchSummary.match.is_home,
        match_type: matchSummary.match.match_type || 'LEAGUE',
        competition: matchSummary.match.competition || '',
        score_for: toInputStringOrEmpty(matchSummary.match.score_for),
        score_against: toInputStringOrEmpty(matchSummary.match.score_against),
        veo_title: matchSummary.match.veo_title || linkedSession?.session_title || '',
        veo_url: matchSummary.match.veo_url || '',
        veo_duration: toInputStringOrEmpty(matchSummary.match.veo_duration),
        veo_camera: matchSummary.match.veo_camera || '',
      }));
      await initializeMatchForms(matchSummary, resolvedTeamName);
    } catch (err) {
      if (latestSelectedMatchRequest.current !== requestId) {
        return;
      }
      console.error(err);
      setFlash('Erreur lors du chargement du match Veo selectionne', 'error');
      setSummary(null);
    } finally {
      if (latestSelectedMatchRequest.current === requestId) {
        setSaving(false);
      }
    }
  };

  useEffect(() => {
    loadVeoBootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedMatchId) {
      resetSelectedMatchState();
      loadSelectedMatch(selectedMatchId);
    } else {
      latestSelectedMatchRequest.current = 0;
      resetSelectedMatchState();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId]);

  useEffect(() => {
    if (!selectedCatapultSession) {
      return;
    }

    const catapultTeam = catapultTeams.find(
      (team) => Number(team.id) === Number(selectedCatapultSession.team_id)
    );
    const normalizedSessionTitle = (selectedCatapultSession.session_title || '').trim().toLowerCase();
    const selectedDate = matchForm.date || selectedCatapultSession.date;
    const existingMatchesOnDate = matches.filter((match) => match.date === selectedDate);
    const existingMatch =
      existingMatchesOnDate.find(
        (match) => (match.veo_title || '').trim().toLowerCase() === normalizedSessionTitle
      ) || existingMatchesOnDate[0] || null;
    const inferredOpponent = inferOpponentFromSessionTitle(selectedCatapultSession.session_title);

    setMatchForm((prev) => ({
      ...prev,
      team_name: catapultTeam?.name || prev.team_name,
      opponent_name: existingMatch?.opponent_name || inferredOpponent || '',
      match_type: existingMatch?.match_type || prev.match_type,
      competition: existingMatch?.competition ?? prev.competition,
      score_for: existingMatch ? toInputStringOrEmpty(existingMatch.score_for) : prev.score_for,
      score_against: existingMatch ? toInputStringOrEmpty(existingMatch.score_against) : prev.score_against,
      veo_title: existingMatch?.veo_title || selectedCatapultSession.session_title,
      veo_url: existingMatch?.veo_url || prev.veo_url,
      veo_duration: existingMatch ? toInputStringOrEmpty(existingMatch.veo_duration) : prev.veo_duration,
      veo_camera: existingMatch?.veo_camera || prev.veo_camera,
    }));
  }, [selectedCatapultSession, catapultTeams, matches, matchForm.date]);

  const handleMatchFormChange = (field, value) => {
    if (field === 'date') {
      const sessions = catapultSessions.filter((session) => session.date === value);
      const defaultSession = sessions[0] || null;
      const existingMatch = matches.find((match) => match.date === value) || null;
      const existingTeam = existingMatch
        ? catapultTeams.find((team) => Number(team.id) === Number(existingMatch.team_id))
        : null;
      const inferredOpponent = defaultSession
        ? inferOpponentFromSessionTitle(defaultSession.session_title)
        : '';

      setSelectedCatapultSessionTitle(defaultSession?.session_title || '');
      setMatchForm((prev) => ({
        ...prev,
        date: value,
        team_name: existingTeam?.name || prev.team_name,
        opponent_name: inferredOpponent || existingMatch?.opponent_name || '',
        match_type: existingMatch?.match_type || prev.match_type,
        competition: existingMatch?.competition ?? '',
        score_for: existingMatch ? toInputStringOrEmpty(existingMatch.score_for) : '',
        score_against: existingMatch ? toInputStringOrEmpty(existingMatch.score_against) : '',
        veo_title: defaultSession?.session_title || existingMatch?.veo_title || '',
        veo_url: existingMatch?.veo_url || '',
        veo_duration: existingMatch ? toInputStringOrEmpty(existingMatch.veo_duration) : '',
        veo_camera: existingMatch?.veo_camera || '',
      }));
      return;
    }

    setMatchForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateVeoSession = async (event) => {
    event.preventDefault();

    if (!matchForm.date) {
      setFlash('La date de session est obligatoire', 'error');
      return;
    }

    const selectedTeamName = matchForm.team_name?.trim();
    let sessionTitle = selectedCatapultSession?.session_title?.trim();
    let teamName = selectedTeamName;
    let playerNames = [];

    if (selectedCatapultSession) {
      const catapultTeam = catapultTeams.find(
        (team) => Number(team.id) === Number(selectedCatapultSession.team_id)
      );
      if (!catapultTeam?.name) {
        setFlash("Impossible d'identifier l'equipe Catapult de la seance selectionnee", 'error');
        return;
      }
      teamName = catapultTeam.name;
      playerNames = await catapultService.getSessionPlayersByTitle(selectedCatapultSession.session_title);
    }

    if (!teamName) {
      setFlash('Selectionne une equipe pour creer la session Veo', 'error');
      return;
    }

    if (!sessionTitle) {
      sessionTitle = matchForm.veo_title?.trim() || `Session Veo ${matchForm.date}`;
    }

    const inferredOpponent = inferOpponentFromSessionTitle(sessionTitle);
    const isMatchSession = sessionTitle.toUpperCase().includes('MATCH');

    try {
      setSaving(true);
      const result = await veoService.bootstrapFromCatapultSession({
        session_title: sessionTitle,
        session_date: matchForm.date,
        team_name: teamName,
        player_names: playerNames,
        opponent_name: matchForm.opponent_name?.trim() || inferredOpponent || sessionTitle,
        is_home: !!matchForm.is_home,
        match_type: matchForm.match_type || (isMatchSession ? 'LEAGUE' : 'FRIENDLY'),
        competition: matchForm.competition || null,
        score_for: toNumberOrNull(matchForm.score_for, parseInt),
        score_against: toNumberOrNull(matchForm.score_against, parseInt),
        veo_title: matchForm.veo_title?.trim() || sessionTitle,
        veo_url: matchForm.veo_url || null,
        veo_duration: toNumberOrNull(matchForm.veo_duration, parseInt),
        veo_camera: matchForm.veo_camera || null,
        replace_participations: false,
      });

      await refreshMatches(result.match_id);
      setSelectedMatchId(String(result.match_id));
      setActiveWorkflowStep('IMPORT');
      setFlash(
        `Session VEO creee: ${result.created_players} joueur(s) ajoute(s), ${result.participations_created} participation(s)`
      );
    } catch (err) {
      console.error(err);
      setFlash(err.response?.data?.detail || 'Erreur lors de la creation de la session Veo', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteVeoSession = async (match) => {
    if (!match?.id) {
      return;
    }

    const confirmed = window.confirm(
      `Supprimer la session VEO "${formatMatchLabel(match)}" ?\n\nLes participations et metriques associees seront aussi supprimees.`
    );
    if (!confirmed) {
      return;
    }

    const matchId = String(match.id);
    const wasSelected = matchId === String(selectedMatchId);

    try {
      setDeletingMatchId(matchId);
      setSaving(true);
      await veoService.deleteMatch(Number(match.id));
      const refreshedMatches = await refreshMatches();

      if (wasSelected) {
        latestSelectedMatchRequest.current += 1;
        const nextMatch = refreshedMatches.find((item) => String(item.id) !== matchId) || null;
        setSelectedMatchId(nextMatch ? String(nextMatch.id) : '');
        if (!nextMatch) {
          resetSelectedMatchState();
          setActiveWorkflowStep('SESSION');
        }
      }

      setFlash('Session VEO supprimee');
    } catch (err) {
      console.error(err);
      setFlash(err.response?.data?.detail || 'Erreur lors de la suppression de la session VEO', 'error');
    } finally {
      setDeletingMatchId('');
      setSaving(false);
    }
  };

  const handleParticipationChange = (playerId, field, value) => {
    setParticipationState((prev) => ({
      ...prev,
      [playerId]: {
        ...(prev[playerId] || {}),
        [field]: value,
      },
    }));
  };

  const handleSaveParticipations = async () => {
    if (!selectedMatchId) {
      return;
    }

    const payload = Object.entries(participationState)
      .filter(([, value]) => value.selected)
      .map(([playerId, value]) => ({
        player_id: Number(playerId),
        is_starter: !!value.is_starter,
        is_captain: !!value.is_captain,
        minutes_played: toNumberOrNull(value.minutes_played, parseInt),
        position_played: value.position_played || null,
      }));

    try {
      setSaving(true);
      await veoService.updateMatchParticipations(Number(selectedMatchId), payload);
      await loadSelectedMatch(selectedMatchId);
      setFlash('Participations enregistrees');
    } catch (err) {
      console.error(err);
      setFlash(
        err.response?.data?.detail || 'Erreur lors de la sauvegarde des participations',
        'error'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTeamMetrics = async () => {
    if (!selectedMatchId) return;

    const payloadByKey = new Map();

    Object.entries(teamMetricInputs).forEach(([key, raw]) => {
      const metricField = teamMetricFieldByInputKey.get(key);
      if (!metricField) return;

      if (raw === "" || raw === null || raw === undefined) return;

      const value = Number(raw);
      if (Number.isNaN(value)) return;

      payloadByKey.set(makeTeamMetricKey(metricField.saveSlug, metricField.inputSide), {
        metric_slug: metricField.saveSlug,
        side: metricField.inputSide,
        value,
      });
    });

    const values = Array.from(payloadByKey.values());

    try {
      setSaving(true);

      const result = await veoService.updateTeamMetrics(Number(selectedMatchId), values);

      if (result.errors?.length) {
        setFlash(`Sauvegarde partielle: ${result.errors.join(" | ")}`, "error");
        // Stay in EDIT so user can fix
      } else {
        setFlash("Metriques equipe enregistrees");

        // ✅ Back to bars after a clean save
        setTeamMetricsView("BARS");
      }

      await loadSelectedMatch(selectedMatchId);
    } catch (err) {
      console.error(err);
      setFlash(err.response?.data?.detail || "Erreur lors de la sauvegarde des metriques equipe", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleSavePlayerMetrics = async () => {
    if (!selectedMatchId) {
      return;
    }
    if (playerMetricValidation.errors.length > 0) {
      setFlash(playerMetricValidation.errors[0], 'error');
      return;
    }

    const selectedPlayers = players.filter((player) => participationState[player.id]?.selected);
    const selectedPlayerIds = new Set(selectedPlayers.map((player) => Number(player.id)));
    const zeroMinutePlayerIds = new Set(
      selectedPlayers
        .filter((player) => getParticipationMinutesValue(participationState[player.id]) <= 0)
        .map((player) => Number(player.id))
    );
    const valuesByKey = new Map();

    selectedPlayers.forEach((player) => {
      const normalizedPlayerId = Number(player.id);
      if (!selectedPlayerIds.has(normalizedPlayerId) || zeroMinutePlayerIds.has(normalizedPlayerId)) {
        return;
      }
      allFlatPlayerMetrics.forEach((metric) => {
        if (!knownPlayerMetricSlugs.has(metric.slug)) {
          return;
        }
        const raw = getDisplayedPlayerMetricInputValue(normalizedPlayerId, metric.slug, true);
        const value = getNumericInputValue(raw) ?? 0;
        valuesByKey.set(`${normalizedPlayerId}__${metric.slug}`, {
          player_id: normalizedPlayerId,
          metric_slug: metric.slug,
          value,
        });
      });
    });

    zeroMinutePlayerIds.forEach((playerId) => {
      allFlatPlayerMetrics.forEach((metric) => {
        if (!knownPlayerMetricSlugs.has(metric.slug)) {
          return;
        }
        valuesByKey.set(`${playerId}__${metric.slug}`, {
          player_id: playerId,
          metric_slug: metric.slug,
          value: 0,
        });
      });
    });

    const values = Array.from(valuesByKey.values());

    try {
      setSaving(true);
      const result = await veoService.updatePlayerMetrics(Number(selectedMatchId), values);
      if (result.errors?.length) {
        setFlash(`Sauvegarde partielle: ${result.errors.join(' | ')}`, 'error');
      } else {
        const warningSuffix = playerMetricValidation.warnings.length > 0
          ? ` A verifier: ${playerMetricValidation.warnings[0]}`
          : '';
        setFlash(`Metriques joueurs enregistrees. Les champs vides et joueurs sans temps de jeu sont a 0.${warningSuffix}`);
      }
      await loadSelectedMatch(selectedMatchId);
    } catch (err) {
      console.error(err);
      setFlash(
        err.response?.data?.detail || "Erreur lors de la sauvegarde des metriques joueurs",
        'error'
      );
    } finally {
      setSaving(false);
    }
  };

  const renderTeamMetricInput = (field) => {
    const key = makeTeamMetricKey(field.inputSlug, field.inputSide);
    const metaLabel = getMetricMetaLabel(field.metric, { showSide: false });

    return (
      <label key={key} className="block rounded-md border border-gray-200 bg-gray-50/40 p-3">
        <div className="min-h-8.5">
          <span className="block text-xs font-medium text-gray-700">
            {getMetricDisplayLabel(field.metric)}
          </span>
          {metaLabel && <span className="block text-[11px] text-gray-500">{metaLabel}</span>}
        </div>
        <input
          type="number"
          step={field.metric.datatype === 'INT' ? '1' : '0.01'}
          className="mt-2 w-full h-10 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          value={teamMetricInputs[key] ?? ''}
          onChange={(e) => setTeamMetricInputs((prev) => ({ ...prev, [key]: e.target.value }))}
        />
      </label>
    );
  };

  /**
   * Team metrics renderer (BARS by default, EDIT on demand).
   *
   * UX:
   * - Default view = bars (read-only summary).
   * - Button switches to EDIT (inputs).
   * - In EDIT, you can choose essential vs full catalog.
   * - After saving, we automatically return to BARS.
   *
   * Prereqs in Veo.jsx:
   *   const [teamMetricsView, setTeamMetricsView] = useState("BARS"); // "BARS" | "EDIT"
   *   const [showAllMetrics, setShowAllMetrics] = useState(false);   // essential by default in EDIT
   *
   * In handleSaveTeamMetrics (on success), add:
   *   setTeamMetricsView("BARS");
   *   setShowAllMetrics(false);
   *
   * And make sure you imported your bars component:
   *   import StatsBarsPanel from "../components/veo/StatsBarsPanel";
   */
  const renderTeamMetricsInputs = ({ embedded = false } = {}) => {
    const isBars = teamMetricsView === "BARS";

    return (
      <details
        className={embedded ? "group" : "bg-white rounded-lg shadow group"}
        open
      >
        <summary
          className={`cursor-pointer select-none flex items-center justify-between ${
            embedded ? "px-0 py-0" : "px-6 py-4"
          }`}
        >
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              Metriques equipe
            </h3>
            <p className="text-xs text-gray-500">
              Clique pour replier / déplier
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Toggle view button */}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault(); // empêche le toggle du <details>
                setTeamMetricsView(isBars ? "EDIT" : "BARS");
              }}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {isBars ? "Afficher / Modifier les champs" : "Retour aux barres"}
            </button>

            {/* Save button (unique) */}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                handleSaveTeamMetrics();
              }}
              disabled={saving}
              className="bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              Enregistrer metriques equipe
            </button>

            {/* Chevron */}
            <span className="text-xs text-gray-400 ml-2 transition-transform duration-200 group-open:rotate-180">
              ▼
            </span>
          </div>
        </summary>

        <div className={`${embedded ? "px-0 pb-0" : "px-6 pb-6"} space-y-4`}>
          {isBars ? (
            <>
            <StatsBarsPanel
              summary={summary}
              teamMetricInputs={teamMetricInputs}
              clubShortLabel="Notre equipe"
              opponentShortLabel="Adversaire"
              embedded
            />
            {shotmapToDisplay ? (
              <div className="mt-4">
                <ShotmapOverview parsedShotmap={shotmapToDisplay} embedded />
              </div>
            ) : null}
          </>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex rounded-md border border-gray-300 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setTeamMetricsMenu("OWN")}
                    className={`px-3 py-2 text-sm font-medium ${
                      teamMetricsMenu === "OWN"
                        ? "bg-blue-600 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    Notre equipe
                  </button>

                  <button
                    type="button"
                    onClick={() => setTeamMetricsMenu("OPPONENT")}
                    className={`px-3 py-2 text-sm font-medium ${
                      teamMetricsMenu === "OPPONENT"
                        ? "bg-blue-600 text-white"
                        : "bg-white text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    Adversaire
                  </button>
                </div>

                <p className="text-xs text-gray-500">
                  {teamMetricsMenu === "OWN"
                    ? "Saisie des indicateurs de notre equipe."
                    : "Saisie des indicateurs miroir de l'adversaire."}
                </p>
              </div>

              {allTeamMetricFieldsByCategory.map((group) => {
                const sideFields = group.fields.filter(
                  (field) => field.inputSide === teamMetricsMenu
                );
                if (sideFields.length === 0) return null;

                return (
                  <details
                    key={`${group.category}-${teamMetricsMenu}`}
                    className="border rounded-md p-4"
                    open
                  >
                    <summary className="font-semibold text-gray-800 mb-3 cursor-pointer">
                      {group.category_label_fr}
                    </summary>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {sideFields.map(renderTeamMetricInput)}
                    </div>
                  </details>
                );
              })}
            </>
          )}
        </div>
      </details>
    );
  };

  const renderWorkflowStepper = () => (
    <div className="bg-white/90 rounded-lg shadow p-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {VEO_WORKFLOW_STEPS.map((step, index) => {
          const isActive = activeWorkflowStep === step.key;
          const isLocked = step.key !== 'SESSION' && !summary;
          return (
            <button
              key={step.key}
              type="button"
              disabled={isLocked}
              onClick={() => setActiveWorkflowStep(step.key)}
              className={`text-left rounded-md border p-3 transition ${
                isActive
                  ? 'border-blue-600 bg-blue-50 text-blue-900'
                  : isLocked
                    ? 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-blue-300 hover:bg-blue-50/60'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                    isActive ? 'bg-blue-600 text-white' : isLocked ? 'bg-gray-200 text-gray-400' : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {index + 1}
                </span>
                <span className="font-semibold">{step.label}</span>
              </div>
              <p className="mt-2 text-xs">{step.helper}</p>
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderSelectedMatchHeader = () => {
    if (!summary) return null;
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-500">Session active</p>
            <h2 className="text-2xl font-bold text-gray-900">
              {summary.match.opponent_name || 'Match VEO'}
            </h2>
            <p className="text-sm text-gray-600">
              {summary.match.date} • Score {summary.match.score_for ?? 0}-{summary.match.score_against ?? 0}
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadSelectedMatch(selectedMatchId)}
            className="inline-flex items-center justify-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            disabled={saving}
          >
            Rafraichir
          </button>
        </div>
      </div>
    );
  };

  const renderDataQualityPanel = () => {
    if (!summary) return null;
    return (
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <h3 className="text-xl font-semibold text-gray-900">Qualite des donnees</h3>
          <p className="mt-1 text-sm text-gray-600">
            Les alertes ci-dessous indiquent quoi corriger avant de partager le rapport.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-medium uppercase text-gray-500">Metriques equipe</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {veoQuality.teamMetricsFilled}
              {veoQuality.expectedTeamMetricCells > 0 ? ` / ${veoQuality.expectedTeamMetricCells}` : ''}
            </p>
            <div className="mt-3 h-2 rounded bg-gray-200 overflow-hidden">
              <div
                className="h-2 bg-blue-600"
                style={{ width: `${Math.max(0, Math.min(100, veoQuality.teamCompletionPct ?? 0))}%` }}
              />
            </div>
          </div>

          <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-medium uppercase text-gray-500">Metriques joueurs</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {veoQuality.playerMetricValuesFilled}
              {veoQuality.expectedPlayerMetricCells > 0 ? ` / ${veoQuality.expectedPlayerMetricCells}` : ''}
            </p>
            <div className="mt-3 h-2 rounded bg-gray-200 overflow-hidden">
              <div
                className="h-2 bg-emerald-600"
                style={{ width: `${Math.max(0, Math.min(100, veoQuality.playerCompletionPct ?? 0))}%` }}
              />
            </div>
          </div>
        </div>

        <div className="space-y-2">
          {veoQuality.actions.map((action) => (
            <div
              key={action.key}
              className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-md border p-3 ${
                action.tone === 'success'
                  ? 'border-emerald-200 bg-emerald-50'
                  : action.tone === 'danger'
                    ? 'border-rose-200 bg-rose-50'
                    : 'border-orange-200 bg-orange-50'
              }`}
            >
              <div>
                <p className="text-sm font-semibold text-gray-900">{action.label}</p>
                <p className="text-xs text-gray-600">{action.detail}</p>
              </div>
              {action.tone !== 'success' && action.targetStep && action.targetStep !== activeWorkflowStep && (
                <button
                  type="button"
                  onClick={() => setActiveWorkflowStep(action.targetStep)}
                  className="self-start sm:self-auto rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                >
                  Corriger
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderReportPreview = () => {
    if (!summary) return null;
    return (
      <div className="space-y-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Rapport VEO</p>
              <h3 className="text-2xl font-bold text-gray-900">{summary.match.veo_title || summary.match.opponent_name}</h3>
              <p className="mt-1 text-sm text-gray-600">Synthese factuelle des donnees importees et verifiees.</p>
            </div>
            {selectedSessionReportPath ? (
              <Link
                to={selectedSessionReportPath}
                className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Ouvrir le rapport dans la session
              </Link>
            ) : (
              <p className="rounded-md bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
                Aucun lien Catapult explicite pour cette session.
              </p>
            )}
          </div>

          <div className="mt-5 grid grid-cols-2 lg:grid-cols-6 gap-3">
            {veoReportAnalysis.reportKpis.map((kpi) => (
              <div key={kpi.label} className="rounded-md border border-gray-200 bg-gray-50 p-3">
                <p className="text-xs uppercase text-gray-500">{kpi.label}</p>
                <p className="mt-1 text-xl font-bold text-gray-900">{kpi.value}</p>
              </div>
            ))}
          </div>
        </div>
        {renderDataQualityPanel()}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <StatsBarsPanel
            summary={summary}
            teamMetricInputs={teamMetricInputs}
            clubShortLabel="Notre equipe"
            opponentShortLabel="Adversaire"
            embedded
          />
          {shotmapToDisplay ? <ShotmapOverview parsedShotmap={shotmapToDisplay} embedded /> : null}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0 space-y-6">
        <div>
          <h1 className="justify-self-start inline-block bg-white/50 px-4 py-2 rounded-md text-4xl font-bold text-black">
            VEO
          </h1>
          <p className="block w-fit bg-white/50 px-4 py-2 rounded-md text-xl text-black">
            Saisie manuelle des matchs et stats Veo pour centraliser les rapports.
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}
        {success && (
          <div className="rounded-md bg-green-50 p-4">
            <p className="text-sm text-green-800">{success}</p>
          </div>
        )}

        <div className="bg-blue-50/80 border border-blue-100 rounded-lg p-4">
          <p className="text-sm font-semibold text-blue-900">
            Catalogue exhaustif VEO: {metricCatalogStats.totalTeam} metriques equipe,{' '}
            {metricCatalogStats.totalPlayer} metriques joueurs.
          </p>
          <p className="mt-1 text-xs text-blue-800">
            Les champs sont regroupes par categories. Le bouton "Afficher tous les champs" permet la saisie complete
            pour un rapport VEO detaille.
          </p>
          <details className="mt-3">
            <summary className="cursor-pointer text-xs font-medium text-blue-900">
              Voir le detail des categories
            </summary>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-blue-900">
              <div>
                <p className="font-semibold">Equipe</p>
                <ul className="mt-1 space-y-1">
                  {metricCatalogStats.teamByCategory.map((category) => (
                    <li key={`team-${category.category}`}>
                      {category.category}: {category.count}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-semibold">Joueurs</p>
                <ul className="mt-1 space-y-1">
                  {metricCatalogStats.playerByCategory.map((category) => (
                    <li key={`player-${category.category}`}>
                      {category.category}: {category.count}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
        </div>

        {renderWorkflowStepper()}

        {activeWorkflowStep === 'SESSION' && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <form
            onSubmit={handleCreateVeoSession}
            className="bg-white/80 rounded-lg shadow p-6 space-y-4"
          >
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Creer une nouvelle session VEO</h2>
              <p className="mt-1 text-sm text-gray-600">
                La session est rattachee automatiquement a une seance Catapult de la meme date si elle existe.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="text-xs font-medium text-gray-600">Date de session</span>
                <input
                  type="date"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.date}
                  onChange={(e) => handleMatchFormChange('date', e.target.value)}
                  required
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Seance Catapult (optionnel)</span>
                <select
                  className={FORM_CONTROL_CLASS}
                  value={selectedCatapultSessionTitle}
                  onChange={(e) => setSelectedCatapultSessionTitle(e.target.value)}
                >
                  <option value="">Aucune (creation manuelle)</option>
                  {catapultSessionsForDate.map((session) => (
                    <option key={session.session_title} value={session.session_title}>
                      {session.session_title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Equipe</span>
                <select
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.team_name}
                  onChange={(e) => handleMatchFormChange('team_name', e.target.value)}
                  required
                >
                  <option value="">Selectionner une equipe</option>
                  {catapultTeams.map((team) => (
                    <option key={team.id} value={team.name}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Adversaire</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Ex: Racing Besancon"
                  value={matchForm.opponent_name}
                  onChange={(e) => handleMatchFormChange('opponent_name', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Type</span>
                <select
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.match_type}
                  onChange={(e) => handleMatchFormChange('match_type', e.target.value)}
                >
                  {MATCH_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Competition</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Championnat, Coupe..."
                  value={matchForm.competition}
                  onChange={(e) => handleMatchFormChange('competition', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Buts marques</span>
                <input
                  type="number"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.score_for}
                  onChange={(e) => handleMatchFormChange('score_for', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-600">Buts encaisses</span>
                <input
                  type="number"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.score_against}
                  onChange={(e) => handleMatchFormChange('score_against', e.target.value)}
                />
              </label>

              <label className="block sm:col-span-2">
                <span className="text-xs font-medium text-gray-600">Titre session VEO (optionnel)</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Par defaut: titre de seance Catapult"
                  value={matchForm.veo_title}
                  onChange={(e) => handleMatchFormChange('veo_title', e.target.value)}
                />
              </label>
            </div>

            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={matchForm.is_home}
                onChange={(e) => handleMatchFormChange('is_home', e.target.checked)}
              />
              Match a domicile
            </label>

            <details className="border rounded-md p-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-700">
                Reference video (facultatif)
              </summary>
              <p className="mt-2 text-xs text-gray-600">
                Ces champs servent uniquement a garder la trace de la video Veo (lien, duree, camera). Ils n'impactent
                pas le calcul des statistiques ni le rapport.
              </p>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  className="h-10 border border-gray-300 rounded-md px-3 py-2 text-sm sm:col-span-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="URL de la video Veo"
                  value={matchForm.veo_url}
                  onChange={(e) => handleMatchFormChange('veo_url', e.target.value)}
                />
                <input
                  type="number"
                  className="h-10 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Duree video (secondes)"
                  value={matchForm.veo_duration}
                  onChange={(e) => handleMatchFormChange('veo_duration', e.target.value)}
                />
                <input
                  className="h-10 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Modele camera (ex: Veo Cam 2)"
                  value={matchForm.veo_camera}
                  onChange={(e) => handleMatchFormChange('veo_camera', e.target.value)}
                />
              </div>
            </details>

            {matchForm.date && (
              <div className="rounded-md bg-gray-50 p-3 text-xs text-gray-600">
                {catapultSessionsForDate.length > 0
                  ? `Seances Catapult trouvees ce jour: ${catapultSessionsForDate.length}.`
                  : 'Aucune seance Catapult sur cette date: creation manuelle possible.'}
              </div>
            )}

            <button
              type="submit"
              disabled={saving}
              className="w-full bg-blue-600 text-white rounded-md px-3 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              Creer la session VEO
            </button>
          </form>

          <div className="bg-white/80 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Sessions VEO existantes</h2>
            {matches.length === 0 ? (
              <p className="text-sm text-gray-500">Aucune session VEO creee.</p>
            ) : (
              <>
                <select
                  className="w-full border rounded-md px-3 py-2 text-sm mb-4"
                  value={selectedMatchId}
                  onChange={(e) => setSelectedMatchId(e.target.value)}
                >
                  <option value="">Selectionner une session</option>
                  {matches.map((match) => (
                    <option key={match.id} value={String(match.id)}>
                      {formatMatchLabel(match)}
                    </option>
                  ))}
                </select>
                <ul className="max-h-72 overflow-auto divide-y border rounded-md">
                  {matches.map((match) => (
                    <li
                      key={match.id}
                      className={`flex items-center gap-2 px-3 py-2 ${
                        String(match.id) === selectedMatchId ? 'bg-blue-50' : 'hover:bg-gray-50'
                      }`}
                    >
                      <button
                        type="button"
                        className="min-w-0 flex-1 text-left"
                        onClick={() => setSelectedMatchId(String(match.id))}
                      >
                        <p className="truncate text-sm font-medium text-gray-900">{match.opponent_name}</p>
                        <p className="truncate text-xs text-gray-500">
                          {match.date} • {match.match_type} • {match.score_for ?? 0}-{match.score_against ?? 0}
                        </p>
                      </button>
                      <button
                        type="button"
                        title="Supprimer la session VEO"
                        aria-label={`Supprimer ${formatMatchLabel(match)}`}
                        disabled={saving || deletingMatchId === String(match.id)}
                        onClick={() => handleDeleteVeoSession(match)}
                        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-red-200 text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <TrashIcon className="h-4 w-4" aria-hidden="true" />
                        <span className="sr-only">Supprimer</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
        )}

        {summary && (
          <div className="space-y-6">
            {renderSelectedMatchHeader()}

            {activeWorkflowStep === 'REPORT' && renderReportPreview()}

            {activeWorkflowStep === 'IMPORT' && (
            <SmartPastePanel
              entrySchema={entrySchema}
              selectedMatchId={selectedMatchId ? Number(selectedMatchId) : null}
              teamMetricInputs={teamMetricInputs}
              setTeamMetricInputs={setTeamMetricInputs}
              setFlash={setFlash}
              onParsedChange={setSmartPasteParsed} 
            />
            )}

            {activeWorkflowStep === 'VERIFY' && renderDataQualityPanel()}

            {activeWorkflowStep === 'VERIFY' && (
            <details className="bg-white rounded-lg shadow group" open>
              <summary className="cursor-pointer select-none px-6 py-4 flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Participations</h3>
                  <p className="text-xs text-gray-500 ">Clique pour replier / déplier</p>
                </div>
                <span className="text-xs text-gray-400 transition-transform duration-200 group-open:rotate-180">▼</span>
              </summary>

              <div className="px-6 pb-6">
                <div className="flex items-center justify-between mb-4">
                  <div />
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault(); // évite de toggle le details
                      handleSaveParticipations();
                    }}
                    disabled={saving}
                    className="bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    Enregistrer participations
                  </button>
                </div>

                <div className="overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left border-b">
                        <th className="py-2 pr-3">Joueur</th>
                        <th className="py-2 pr-3">Selection</th>
                        <th className="py-2 pr-3">Titulaire</th>
                        <th className="py-2 pr-3">Capitaine</th>
                        <th className="py-2 pr-3">Minutes</th>
                        <th className="py-2 pr-3">Poste joue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {players.map((player) => {
                        const state = participationState[player.id] || {};
                        return (
                          <tr key={player.id} className="border-b last:border-b-0">
                            <td className="py-2 pr-3">{formatPlayerDisplayName(player)}</td>
                            <td className="py-2 pr-3">
                              <input
                                type="checkbox"
                                checked={!!state.selected}
                                onChange={(e) =>
                                  handleParticipationChange(player.id, "selected", e.target.checked)
                                }
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                type="checkbox"
                                checked={!!state.is_starter}
                                disabled={!state.selected}
                                onChange={(e) =>
                                  handleParticipationChange(player.id, "is_starter", e.target.checked)
                                }
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                type="checkbox"
                                checked={!!state.is_captain}
                                disabled={!state.selected}
                                onChange={(e) =>
                                  handleParticipationChange(player.id, "is_captain", e.target.checked)
                                }
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                type="number"
                                className="h-9 w-24 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                value={state.minutes_played ?? ""}
                                disabled={!state.selected}
                                onChange={(e) =>
                                  handleParticipationChange(player.id, "minutes_played", e.target.value)
                                }
                              />
                            </td>
                            <td className="py-2 pr-3">
                              <input
                                className="h-9 w-32 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                value={state.position_played ?? ""}
                                disabled={!state.selected}
                                onChange={(e) =>
                                  handleParticipationChange(player.id, "position_played", e.target.value)
                                }
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </details>
            )}

            {/* ✅ Metrics team: use renderer (no duplicated JSX, no "mode simplifie") */}
            {activeWorkflowStep === 'IMPORT' && (
            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              {renderTeamMetricsInputs({ embedded: true })}
            </div>
            )}

            {activeWorkflowStep === 'VERIFY' && (
            <details className="bg-white rounded-lg shadow group" open>
              <summary className="cursor-pointer select-none px-6 py-4 flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Metriques joueurs</h3>
                  <p className="text-xs text-gray-500">Clique pour replier / déplier</p>
                </div>
                <span className="text-xs text-gray-400 transition-transform duration-200 group-open:rotate-180">▼</span>
              </summary>

              <div className="px-6 pb-6 space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Joueurs presents au match</p>
                    <p className="text-xs text-gray-500">
                      Tri par temps de jeu décroissant. Les titulaires et les joueurs entrés sont signalés pour lire la feuille en quelques secondes.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      handleSavePlayerMetrics();
                    }}
                    disabled={saving}
                    className="bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    Enregistrer metriques joueurs
                  </button>
                </div>

                {rosterSyncMessage && (
                  <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-md px-3 py-2">
                    {rosterSyncMessage}
                  </p>
              )}
              {(Object.keys(autoZeroPlayerMetricReasons).length > 0 ||
                playerMetricValidation.errors.length > 0 ||
                playerMetricValidation.warnings.length > 0) && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {Object.keys(autoZeroPlayerMetricReasons).length > 0 && (
                    <div className="rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
                      <p className="font-semibold">Remplissage automatique</p>
                      <p className="mt-1">
                        {Object.entries(autoZeroPlayerMetricReasons)
                          .map(([slug, reason]) => `${getMetricDisplayLabel({ slug, label_fr: slug })}: 0 (${reason})`)
                          .join(' • ')}
                      </p>
                    </div>
                  )}
                  {(playerMetricValidation.errors.length > 0 || playerMetricValidation.warnings.length > 0) && (
                    <div
                      className={`rounded-md border px-3 py-2 text-xs ${
                        playerMetricValidation.errors.length > 0
                          ? 'border-rose-100 bg-rose-50 text-rose-900'
                          : 'border-orange-100 bg-orange-50 text-orange-900'
                      }`}
                    >
                      <p className="font-semibold">
                        {playerMetricValidation.errors.length > 0 ? 'Incoherence bloquante' : 'A verifier'}
                      </p>
                      <p className="mt-1">
                        {(playerMetricValidation.errors[0] || playerMetricValidation.warnings[0])}
                      </p>
                    </div>
                  )}
                </div>
              )}
              {playersForMetricsGrid.length === 0 ? (
                <p className="text-sm text-gray-500">
                  Aucun joueur selectionne pour ce match. Coche les joueurs presents dans Participations pour saisir leurs metriques.
                </p>
              ) : (
                <div className="overflow-hidden border rounded-md">
                  <table className="w-full table-fixed text-xs">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="w-36 text-left py-2 px-2">Joueur</th>
                        <th className="w-24 text-left py-2 px-2">Statut</th>
                        <th className="w-14 text-left py-2 px-1">Temps</th>
                        {visibleFlatPlayerMetrics.map((metric) => {
                          const metaLabel = getMetricMetaLabel(metric);
                          return (
                            <th key={metric.slug} className="py-2 px-1 text-center align-bottom">
                              <div className="mx-auto max-w-16 truncate font-medium" title={getMetricDisplayLabel(metric)}>
                                {metric.slug === 'player_cards' ? (
                                  <span className="inline-flex items-center justify-center gap-0.5">
                                    <span className="inline-block h-3 w-2 rounded-[1px] bg-yellow-300 ring-1 ring-yellow-500" />
                                    <span className="inline-block h-3 w-2 rounded-[1px] bg-red-500 ring-1 ring-red-700" />
                                  </span>
                                ) : (
                                  getMetricDisplayLabel(metric)
                                )}
                              </div>
                              {metaLabel && <div className="text-[10px] text-gray-500">{metaLabel}</div>}
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {playersForMetricsGrid.map((player) => {
                        const state = participationState[player.id] || {};
                        const minutes = getParticipationMinutesValue(state);
                        const hasMinutes = minutes > 0;
                        const roleLabel = getParticipationRoleLabel(state);
                        const rowClass = state.is_starter
                          ? 'bg-blue-50/80'
                          : hasMinutes
                            ? 'bg-emerald-50/70'
                            : 'bg-white';
                        const badgeClass = state.is_starter
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : hasMinutes
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                            : 'bg-gray-100 text-gray-600 border-gray-200';
                        return (
                        <tr key={player.id} className={`border-b last:border-b-0 ${rowClass}`}>
                          <td className="py-2 px-2 font-medium">
                            <div className="flex items-center gap-2">
                              <span
                                className={`h-2 w-2 rounded-full ${
                                  state.is_starter ? 'bg-blue-600' : hasMinutes ? 'bg-emerald-600' : 'bg-gray-300'
                                }`}
                              />
                              <span className="truncate">{formatPlayerDisplayName(player)}</span>
                            </div>
                          </td>
                          <td className="py-2 px-2">
                            <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${badgeClass}`}>
                              {roleLabel}
                            </span>
                          </td>
                          <td className="py-2 px-1 text-xs font-semibold text-gray-900">
                            {hasMinutes ? `${minutes} min` : '-'}
                          </td>
                          {visibleFlatPlayerMetrics.map((metric) => {
                            const key = makePlayerMetricKey(player.id, metric.slug);
                            const isAutoZero = !!autoZeroPlayerMetricReasons[metric.slug];
                            const displayValue = getDisplayedPlayerMetricInputValue(player.id, metric.slug, hasMinutes);
                            return (
                              <td key={key} className="py-2 px-1">
                                <input
                                  type="number"
                                  min="0"
                                  max={PLAYER_METRIC_MAX_VALUES[metric.slug]}
                                  step={metric.datatype === 'INT' ? '1' : '0.01'}
                                  disabled={!hasMinutes || isAutoZero}
                                  title={isAutoZero ? autoZeroPlayerMetricReasons[metric.slug] : undefined}
                                  className="h-8 w-full min-w-0 rounded border border-gray-300 px-1 py-1 text-center text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                                  value={displayValue}
                                  onChange={(e) =>
                                    setPlayerMetricInputs((prev) => ({
                                      ...prev,
                                      [key]: e.target.value,
                                    }))
                                  }
                                />
                              </td>
                            );
                          })}
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              </div>
          </details>
          )}
        </div>  
        )}
        {!summary && activeWorkflowStep !== 'SESSION' && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">
            Choisis ou cree une session VEO pour continuer ce parcours.
          </div>
        )}
      </div>
    </div>
  );
}
