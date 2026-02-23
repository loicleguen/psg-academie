import { useEffect, useMemo, useRef, useState } from 'react';
import { veoService } from '../services/veoService';
import { catapultService } from '../services/catapultService';

const MATCH_TYPES = ['LEAGUE', 'CUP', 'FRIENDLY', 'TOURNAMENT'];

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
  'player_goals',
  'player_shots',
  'player_goal_assists',
  'player_total_events',
  'player_corners',
  'player_free_kicks',
  'player_throw_ins',
]);

const METRIC_LABEL_OVERRIDES = {
  player_total_events: 'Total evenements',
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
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [players, setPlayers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [entrySchema, setEntrySchema] = useState(null);

  const [selectedMatchId, setSelectedMatchId] = useState('');
  const [summary, setSummary] = useState(null);
  const [matchForm, setMatchForm] = useState(EMPTY_MATCH_FORM);

  const [participationState, setParticipationState] = useState({});
  const [teamMetricInputs, setTeamMetricInputs] = useState({});
  const [playerMetricInputs, setPlayerMetricInputs] = useState({});
  const [catapultSessions, setCatapultSessions] = useState([]);
  const [catapultTeams, setCatapultTeams] = useState([]);
  const [selectedCatapultSessionTitle, setSelectedCatapultSessionTitle] = useState('');
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const [teamMetricsMenu, setTeamMetricsMenu] = useState('OWN');
  const latestSelectedMatchRequest = useRef(0);

  const teamMetricsByCategory = entrySchema?.team_metrics_by_category ?? [];
  const playerMetricsByCategory = entrySchema?.player_metrics_by_category ?? [];

  const visibleTeamMetricsByCategory = useMemo(() => {
    if (showAllMetrics) {
      return teamMetricsByCategory;
    }
    return teamMetricsByCategory
      .map((group) => ({
        ...group,
        metrics: group.metrics.filter((metric) => ESSENTIAL_TEAM_METRICS.has(metric.slug)),
      }))
      .filter((group) => group.metrics.length > 0);
  }, [teamMetricsByCategory, showAllMetrics]);

  const visiblePlayerMetricsByCategory = useMemo(() => {
    if (showAllMetrics) {
      return playerMetricsByCategory;
    }
    return playerMetricsByCategory
      .map((group) => ({
        ...group,
        metrics: group.metrics.filter((metric) => ESSENTIAL_PLAYER_METRICS.has(metric.slug)),
      }))
      .filter((group) => group.metrics.length > 0);
  }, [playerMetricsByCategory, showAllMetrics]);

  const allTeamMetricFields = useMemo(
    () =>
      teamMetricsByCategory.flatMap((group) =>
        group.metrics.flatMap((metric) => buildTeamMetricFieldConfigs(metric))
      ),
    [teamMetricsByCategory]
  );
  const visibleTeamMetricFieldsByCategory = useMemo(
    () =>
      visibleTeamMetricsByCategory
        .map((group) => ({
          ...group,
          fields: group.metrics.flatMap((metric) => buildTeamMetricFieldConfigs(metric)),
        }))
        .filter((group) => group.fields.length > 0),
    [visibleTeamMetricsByCategory]
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
  const knownPlayerMetricSlugs = useMemo(
    () => new Set(allFlatPlayerMetrics.map((metric) => metric.slug)),
    [allFlatPlayerMetrics]
  );
  const visibleFlatPlayerMetrics = useMemo(
    () => visiblePlayerMetricsByCategory.flatMap((group) => group.metrics),
    [visiblePlayerMetricsByCategory]
  );

  const selectedPlayersForGrid = useMemo(() => {
    const selectedIds = Object.entries(participationState)
      .filter(([, value]) => value.selected)
      .map(([playerId]) => Number(playerId));

    const selected = players.filter((player) => selectedIds.includes(player.id));
    return selected.length > 0 ? selected : players;
  }, [participationState, players]);

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

  const initializeMatchForms = async (matchSummary) => {
    const teamPlayers = await veoService.getPlayers(matchSummary.match.team_id);
    const normalizedPlayers = Array.isArray(teamPlayers) ? teamPlayers : [];
    if (!Array.isArray(teamPlayers)) {
      console.error('Format inattendu depuis Veo API /players:', teamPlayers);
    }
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
      const catapultTeam = catapultTeams.find(
        (team) => Number(team.id) === Number(matchSummary.match.team_id)
      );
      const sessionsSameDate = catapultSessions.filter((session) => session.date === matchDate);
      const normalizedVeoTitle = (matchSummary.match.veo_title || '').trim().toLowerCase();
      const linkedSession =
        sessionsSameDate.find(
          (session) => (session.session_title || '').trim().toLowerCase() === normalizedVeoTitle
        ) || sessionsSameDate[0] || null;

      setSelectedCatapultSessionTitle(linkedSession?.session_title || '');
      setMatchForm((prev) => ({
        ...prev,
        date: matchDate,
        team_name: catapultTeam?.name || prev.team_name,
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
      await initializeMatchForms(matchSummary);
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
  }, []);

  useEffect(() => {
    if (selectedMatchId) {
      resetSelectedMatchState();
      loadSelectedMatch(selectedMatchId);
    } else {
      latestSelectedMatchRequest.current = 0;
      resetSelectedMatchState();
    }
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
    if (!selectedMatchId) {
      return;
    }

    const payloadByKey = new Map();

    Object.entries(teamMetricInputs).forEach(([key, raw]) => {
      const metricField = teamMetricFieldByInputKey.get(key);
      if (!metricField) {
        return;
      }

      if (raw === '' || raw === null || raw === undefined) {
        return;
      }
      const value = Number(raw);
      if (Number.isNaN(value)) {
        return;
      }

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
        setFlash(`Sauvegarde partielle: ${result.errors.join(' | ')}`, 'error');
      } else {
        setFlash('Metriques equipe enregistrees');
      }
      await loadSelectedMatch(selectedMatchId);
    } catch (err) {
      console.error(err);
      setFlash(
        err.response?.data?.detail || "Erreur lors de la sauvegarde des metriques equipe",
        'error'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSavePlayerMetrics = async () => {
    if (!selectedMatchId) {
      return;
    }

    const knownPlayerIds = new Set(players.map((player) => Number(player.id)));

    const values = Object.entries(playerMetricInputs)
      .map(([key, raw]) => {
        if (raw === '' || raw === null || raw === undefined) {
          return null;
        }
        const value = Number(raw);
        if (Number.isNaN(value)) {
          return null;
        }
        const [playerId, metricSlug] = key.split('__');
        const normalizedPlayerId = Number(playerId);
        if (!knownPlayerIds.has(normalizedPlayerId)) {
          return null;
        }
        if (!knownPlayerMetricSlugs.has(metricSlug)) {
          return null;
        }
        return {
          player_id: normalizedPlayerId,
          metric_slug: metricSlug,
          value,
        };
      })
      .filter(Boolean);

    try {
      setSaving(true);
      const result = await veoService.updatePlayerMetrics(Number(selectedMatchId), values);
      if (result.errors?.length) {
        setFlash(`Sauvegarde partielle: ${result.errors.join(' | ')}`, 'error');
      } else {
        setFlash('Metriques joueurs enregistrees');
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

  if (loading) {
    return (
      <div className="veo-page max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="veo-page max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0 space-y-6">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">VEO</h1>
          <p className="mt-2 text-2xl font-bold text-grey-600">
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

        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p className="text-sm font-semibold text-blue-900">
            Catalogue exhaustif VEO: {metricCatalogStats.totalTeam} metriques equipe, {metricCatalogStats.totalPlayer} metriques joueurs.
          </p>
          <p className="mt-1 text-xs text-blue-800">
            Les champs sont regroupes par categories. Le bouton "Afficher tous les champs" permet la saisie complete pour un rapport VEO detaille.
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

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <form onSubmit={handleCreateVeoSession} className="bg-white rounded-lg shadow p-6 space-y-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Creer une nouvelle session VEO</h2>
              <p className="mt-1 text-sm text-gray-900">
                La session est rattachee automatiquement a une seance Catapult de la meme date si elle existe.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block">
                <span className="text-xs font-medium text-gray-900">Date de session</span>
                <input
                  type="date"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.date}
                  onChange={(e) => handleMatchFormChange('date', e.target.value)}
                  required
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-900">Seance Catapult (optionnel)</span>
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
                <span className="text-xs font-medium text-gray-900">Equipe</span>
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
                <span className="text-xs font-medium text-gray-900">Adversaire</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Ex: Racing Besancon"
                  value={matchForm.opponent_name}
                  onChange={(e) => handleMatchFormChange('opponent_name', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-900">Type</span>
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
                <span className="text-xs font-medium text-gray-900">Competition</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Championnat, Coupe..."
                  value={matchForm.competition}
                  onChange={(e) => handleMatchFormChange('competition', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-900">Buts marques</span>
                <input
                  type="number"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.score_for}
                  onChange={(e) => handleMatchFormChange('score_for', e.target.value)}
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-gray-900">Buts encaisses</span>
                <input
                  type="number"
                  className={FORM_CONTROL_CLASS}
                  value={matchForm.score_against}
                  onChange={(e) => handleMatchFormChange('score_against', e.target.value)}
                />
              </label>

              <label className="block sm:col-span-2">
                <span className="text-xs font-medium text-gray-900">Titre session VEO (optionnel)</span>
                <input
                  className={FORM_CONTROL_CLASS}
                  placeholder="Par defaut: titre de seance Catapult"
                  value={matchForm.veo_title}
                  onChange={(e) => handleMatchFormChange('veo_title', e.target.value)}
                />
              </label>
            </div>

            <label className="inline-flex items-center gap-2 text-sm text-gray-900">
              <input
                type="checkbox"
                checked={matchForm.is_home}
                onChange={(e) => handleMatchFormChange('is_home', e.target.checked)}
              />
              Match a domicile
            </label>

            <details className="border rounded-md p-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-900">
                Reference video (facultatif)
              </summary>
              <p className="mt-2 text-xs text-gray-900">
                Ces champs servent uniquement a garder la trace de la video Veo (lien, duree, camera). Ils
                n'impactent pas le calcul des statistiques ni le rapport.
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

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Sessions VEO existantes</h2>
            {matches.length === 0 ? (
              <p className="text-sm text-gray-900">Aucune session VEO creee.</p>
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
                      className={`px-3 py-2 cursor-pointer ${
                        String(match.id) === selectedMatchId ? 'bg-blue-50' : 'hover:bg-gray-50'
                      }`}
                      onClick={() => setSelectedMatchId(String(match.id))}
                    >
                      <p className="text-sm font-medium text-gray-900">{match.opponent_name}</p>
                      <p className="text-xs text-gray-500">
                        {match.date} • {match.match_type} • {match.score_for ?? 0}-{match.score_against ?? 0}
                      </p>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>

        {summary && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    Match selectionne: {summary.match.opponent_name}
                  </h2>
                  <p className="text-sm text-gray-600">
                    {summary.match.date} • Score {summary.match.score_for ?? 0}-{summary.match.score_against ?? 0}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => loadSelectedMatch(selectedMatchId)}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  disabled={saving}
                >
                  Rafraichir
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-900">Participations</h3>
                <button
                  type="button"
                  onClick={handleSaveParticipations}
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
                          <td className="py-2 pr-3">
                            {player.first_name} {player.last_name}
                          </td>
                          <td className="py-2 pr-3">
                            <input
                              type="checkbox"
                              checked={!!state.selected}
                              onChange={(e) =>
                                handleParticipationChange(player.id, 'selected', e.target.checked)
                              }
                            />
                          </td>
                          <td className="py-2 pr-3">
                            <input
                              type="checkbox"
                              checked={!!state.is_starter}
                              disabled={!state.selected}
                              onChange={(e) =>
                                handleParticipationChange(player.id, 'is_starter', e.target.checked)
                              }
                            />
                          </td>
                          <td className="py-2 pr-3">
                            <input
                              type="checkbox"
                              checked={!!state.is_captain}
                              disabled={!state.selected}
                              onChange={(e) =>
                                handleParticipationChange(player.id, 'is_captain', e.target.checked)
                              }
                            />
                          </td>
                          <td className="py-2 pr-3">
                            <input
                              type="number"
                              className="h-9 w-24 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              value={state.minutes_played ?? ''}
                              disabled={!state.selected}
                              onChange={(e) =>
                                handleParticipationChange(player.id, 'minutes_played', e.target.value)
                              }
                            />
                          </td>
                          <td className="py-2 pr-3">
                            <input
                              className="h-9 w-32 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              value={state.position_played ?? ''}
                              disabled={!state.selected}
                              onChange={(e) =>
                                handleParticipationChange(player.id, 'position_played', e.target.value)
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

            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-gray-900">Metriques equipe</h3>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAllMetrics((prev) => !prev)}
                    className="border border-gray-300 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    {showAllMetrics ? 'Mode simplifie' : 'Afficher tous les champs'}
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveTeamMetrics}
                    disabled={saving}
                    className="bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    Enregistrer metriques equipe
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex rounded-md border border-gray-300 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setTeamMetricsMenu('OWN')}
                    className={`px-3 py-2 text-sm font-medium ${
                      teamMetricsMenu === 'OWN'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Notre equipe
                  </button>
                  <button
                    type="button"
                    onClick={() => setTeamMetricsMenu('OPPONENT')}
                    className={`px-3 py-2 text-sm font-medium ${
                      teamMetricsMenu === 'OPPONENT'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Adversaire
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  {teamMetricsMenu === 'OWN'
                    ? 'Saisie des indicateurs de notre equipe.'
                    : "Saisie des indicateurs miroir de l'adversaire."}
                </p>
              </div>

              {visibleTeamMetricFieldsByCategory.map((group) => {
                const sideFields = group.fields.filter((field) => field.inputSide === teamMetricsMenu);
                if (sideFields.length === 0) {
                  return null;
                }

                return (
                  <details key={`${group.category}-${teamMetricsMenu}`} className="border rounded-md p-4" open>
                    <summary className="font-semibold text-gray-800 mb-3 cursor-pointer">
                      {group.category_label_fr}
                    </summary>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {sideFields.map((field) => renderTeamMetricInput(field))}
                    </div>
                  </details>
                );
              })}
            </div>

            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-gray-900">Metriques joueurs</h3>
                <button
                  type="button"
                  onClick={handleSavePlayerMetrics}
                  disabled={saving}
                  className="bg-blue-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  Enregistrer metriques joueurs
                </button>
              </div>
              {selectedPlayersForGrid.length === 0 ? (
                <p className="text-sm text-gray-500">
                  Aucun joueur selectionne. Coche des joueurs dans la section Participations.
                </p>
              ) : (
                <div className="overflow-auto border rounded-md">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left py-2 px-3">Joueur</th>
                        {visibleFlatPlayerMetrics.map((metric) => {
                          const metaLabel = getMetricMetaLabel(metric);
                          return (
                            <th key={metric.slug} className="text-left py-2 px-3 whitespace-nowrap">
                              <div className="font-medium">{getMetricDisplayLabel(metric)}</div>
                              {metaLabel && <div className="text-[10px] text-gray-500">{metaLabel}</div>}
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {selectedPlayersForGrid.map((player) => (
                        <tr key={player.id} className="border-b last:border-b-0">
                          <td className="py-2 px-3 font-medium whitespace-nowrap">
                            {player.first_name} {player.last_name}
                          </td>
                          {visibleFlatPlayerMetrics.map((metric) => {
                            const key = makePlayerMetricKey(player.id, metric.slug);
                            return (
                              <td key={key} className="py-2 px-3">
                                <input
                                  type="number"
                                  step={metric.datatype === 'INT' ? '1' : '0.01'}
                                  className="h-9 w-24 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                  value={playerMetricInputs[key] ?? ''}
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
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}