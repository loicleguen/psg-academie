import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
import api from '../services/api';
import MedicalMap from '../components/MedicalMap';
import { veoService } from '../services/veoService';

const VEO_PLAYER_METRIC_ORDER = [
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

const VEO_PLAYER_METRIC_LABELS = {
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

export default function PlayerDetail() {
  const { playerName } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const compareWith = searchParams.get('compare');

  const [activeTab, setActiveTab] = useState('info');
  const [playerInfo, setPlayerInfo] = useState(null);
  const [playerStats, setPlayerStats] = useState(null);
  const [catapultFilter, setCatapultFilter] = useState('all');
  const [comparePlayers, setComparePlayers] = useState([]);
  const [comparePlayersStats, setComparePlayersStats] = useState([]);
  const [veoStats, setVeoStats] = useState(null);
  const [compareVeoStatsList, setCompareVeoStatsList] = useState([]);
  const [veoFilter, setVeoFilter] = useState('all');
  const [selectedVeoPlayer, setSelectedVeoPlayer] = useState('');
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [veoLoading, setVeoLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [allPlayersInfo, setAllPlayersInfo] = useState([]);
  const [playerSessions, setPlayerSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedSessionStats, setSelectedSessionStats] = useState(null);

    // Medical state
  const [injuries, setInjuries] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [clickCoordinates, setClickCoordinates] = useState(null);
  const [injuryDate, setInjuryDate] = useState('');
  const [injuryEndDate, setInjuryEndDate] = useState('');
  const [injuryComment, setInjuryComment] = useState('');
  const [showEditInjuryModal, setShowEditInjuryModal] = useState(false);
  const [editInjuryForm, setEditInjuryForm] = useState(null);
  const [restrictionDate, setRestrictionDate] = useState('');
  const [restrictionType, setRestrictionType] = useState('no_sport');

  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const passwordFormRef = useRef(null);

  const handlePhotoSelect = async (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      await uploadPhoto(file);
    }
  };

  const uploadPhoto = async (fileParam) => {
    const file = fileParam;
    if (!file || !playerInfo) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const me = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;
      let url = '/auth/me/photo';
      if (me && (me.role === 'admin' || me.role === 'coach') && playerInfo?.id && me.id !== playerInfo.id) {
        url = `/auth/users/${playerInfo.id}/photo`;
      }

      const res = await api.post(url, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      const photo = res.data.photo_url;

      if (url.includes('/auth/me/photo')) {
        setPlayerInfo({ ...playerInfo, photo_url: photo });
        try {
          const meRes = await api.get('/auth/me');
          const me2 = meRes.data;
          if (me2 && me2.id) {
            localStorage.setItem('user', JSON.stringify(me2));
            if (playerInfo?.id === me2.id) {
              setPlayerInfo(me2);
            }
          }
        } catch (err) { console.debug(err); }
      } else {
        try { await loadPlayerInfo(); } catch (err) { console.debug(err); }
      }

    } catch (err) {
      console.error('Upload failed', err);
    }
  };


  const [teams, setTeams] = useState([]);

  useEffect(() => {
    loadPlayerInfo();
    loadPlayerStats();
    loadAllPlayers();
    loadAllPlayersInfo();
    fetchTeams();
    loadVeoStats();
  }, [playerName]);

  // Charger les sessions à l'ouverture de l'onglet Catapult
  useEffect(() => {
    if (activeTab === 'catapult') {
      catapultService.getSessionsByPlayer(playerName).then(sessions => {
        // Filtrer sur les 6 derniers mois
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
        const filtered = sessions
          .filter(s => new Date(s.date) >= sixMonthsAgo)
          .sort((a, b) => new Date(b.date) - new Date(a.date)); // Tri décroissant
        setPlayerSessions(filtered);
      });
    }
  }, [activeTab, playerName]);

  useEffect(() => {
    if (selectedSession) {
      const sessionObj = playerSessions.find(s => s.id === Number(selectedSession));
      if (sessionObj) {
        catapultService.getPlayerSessionStatsJson(sessionObj.session_title, playerName)
          .then(stats => setSelectedSessionStats(stats));
      }
    } else {
      setSelectedSessionStats(null);
    }
  }, [selectedSession, playerName, playerSessions]);

  useEffect(() => {
    // Charger la session sélectionnée au mount
    catapultService.getSelectedSession(playerName).then(res => {
      if (res && res.session_id) {
        setSelectedSession(res.session_id.toString());
      }
    });
  }, [playerName]);

  const fetchTeams = async () => {
    try {
      const res = await api.get('/teams/');
      const data = res.data;
      if (Array.isArray(data)) setTeams(data);
      else if (data && Array.isArray(data.teams)) setTeams(data.teams);
      else if (data && Array.isArray(data.data)) setTeams(data.data);
      else setTeams([]);
    } catch (err) { console.debug('Erreur fetch teams', err); setTeams([]); }
  };

  useEffect(() => {
    if (compareWith && (activeTab === 'catapult' || activeTab === 'veo')) {
      setComparePlayers([compareWith]);
      (async () => {
        try {
          const s = await catapultService.getPlayerStats(compareWith);
          setComparePlayersStats([s]);
        } catch (err) { 
          console.debug(err);
          setComparePlayersStats([]);
        }
      })();
    } else if (activeTab !== 'catapult' && activeTab !== 'veo') {
      setComparePlayers([]);
      setComparePlayersStats([]);
      setCompareVeoStatsList([]);
    }
  }, [compareWith, activeTab]);

  useEffect(() => {
    if (activeTab === 'medical') {
      fetchInjuries();
    }
  }, [activeTab, playerInfo]);

  const loadPlayerInfo = async () => {
    try {
      const cached = localStorage.getItem('user');
      if (cached) {
        try {
          const u = JSON.parse(cached);
          if (u && (u.player_name === playerName || u.full_name === playerName)) {
            setPlayerInfo(u);
            return;
          }
        } catch (err) { console.debug(err); }
      }

      try {
        const meRes = await api.get('/auth/me');
        const me = meRes.data;
        if (me && (me.player_name === playerName || me.full_name === playerName)) {
          setPlayerInfo(me);
          return;
        }
      } catch (err) { console.debug(err); }

      const response = await api.get('/auth/users');
      const player = response.data.find(u => u.player_name === playerName || u.full_name === playerName);
      setPlayerInfo(player);
    } catch (err) { console.debug(err); }
  };

  useEffect(() => {
    if (compareWith) {
      loadCompareVeoStats(compareWith).then(stats => {
        setCompareVeoStatsList(stats ? [stats] : []);
      });
    } else {
      setCompareVeoStatsList([]);
    }
  }, [compareWith]);

  const loadPlayerStats = async () => {
    try {
      setLoading(true);
      const stats = await catapultService.getPlayerStats(playerName);
      setPlayerStats(stats);
    } catch (err) { console.debug(err); } finally {
      setLoading(false);
    }
  };

  const loadVeoStats = async () => {
    try {
      setVeoLoading(true);
      const stats = await veoService.getPlayerMetricsSummaryByName(playerName);
      setVeoStats(stats);
    } catch (error) {
      if (error?.response?.status !== 404) {
        console.error('Erreur chargement stats VEO joueur:', error);
      }
      setVeoStats(null);
    } finally {
      setVeoLoading(false);
    }
  };

  const loadCompareVeoStats = async (name) => {
    try {
      const stats = await veoService.getPlayerMetricsSummaryByName(name);
      return stats ?? null;
    } catch (error) {
      if (error?.response?.status !== 404) {
        console.error('Erreur chargement stats VEO comparaison:', error);
      }
      return null;
    }
  };

  const loadAllPlayers = async () => {
    try {
      const players = await catapultService.getAllPlayers();
      setAllPlayers(players);
    } catch (err) { console.debug(err); }
  };

  const loadAllPlayersInfo = async () => {
    try {
      const response = await api.get('/auth/users');
      setAllPlayersInfo(response.data.filter(u => u.player_name));
    } catch (err) { console.debug(err); }
  };


  const fetchInjuries = async () => {
    if (!playerInfo) return;
    try {
      const res = await api.get(`/players/${playerInfo.id}/injuries`);
      const list = res.data || [];
      list.sort((a,b) => new Date(b.injury_date) - new Date(a.injury_date));
      setInjuries(list);
    } catch (err) { console.debug(err); setInjuries([]); }
  };

  const handleCompare = async () => {
    if (!selectedPlayer || selectedPlayer === playerName) return;
    if (comparePlayers.includes(selectedPlayer)) return;
    if (comparePlayers.length >= 5) {
      alert('Maximum 6 joueurs comparés.');
      return;
    }
    setComparePlayers(prev => [...prev, selectedPlayer]);
    setSelectedPlayer('');

    try {
      const { session_id } = await catapultService.getSelectedSession(selectedPlayer);
      if (!session_id) {
        setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
        alert('Ce joueur n’a pas encore de session sélectionnée !');
        return;
      }
      // Récupère les sessions du joueur comparé
      const sessions = await catapultService.getSessionsByPlayer(selectedPlayer);
      const sessionObj = sessions.find(s => s.id === Number(session_id));
      if (!sessionObj) {
        setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
        alert('Impossible de trouver la session sélectionnée pour ce joueur !');
        return;
      }
      const stats = await catapultService.getPlayerSessionStatsJson(sessionObj.session_title, selectedPlayer);
      if (stats) {
        setComparePlayersStats(prev => [...prev, stats]);
      } else {
        setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
        alert('Impossible de charger les stats pour ' + selectedPlayer);
      }
    } catch (err) {
      setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
      alert(err?.response?.data?.detail || 'Erreur lors de la comparaison');
      console.error(err);
    }
  };

  const clearComparison = () => {
    setSelectedPlayer('');
    setComparePlayers([]);
    setComparePlayersStats([]);
    setCompareVeoStatsList([]);
    setSearchParams({});
  };

  const onCoordinatesClick = (coords) => {
    setClickCoordinates(coords);
    setInjuryDate('');
    setInjuryComment('');
    setShowAddModal(true);
  };

  const addInjury = async () => {
    if (!clickCoordinates) {
      return;
    }
    
    const payload = {
      coord_x: clickCoordinates.coord_x,
      coord_y: clickCoordinates.coord_y,
      injury_date: injuryDate || new Date().toISOString().slice(0,10),
      injury_end_date: injuryEndDate || null,
      restriction_type: restrictionType,
      restriction_date: restrictionDate,
      comment: injuryComment || ''
    };


    try {
      if (playerInfo?.id) {
        const RESPONSE = await api.post(`/players/${playerInfo.id}/injuries`, payload);
        await fetchInjuries();
      } else {
        throw new Error('no player id');
      }
    } catch (err) { console.debug(err); const newList = [{ ...payload, created_at: new Date().toISOString() }, ...injuries];
      newList.sort((a,b) => new Date(b.injury_date) - new Date(a.injury_date));
      setInjuries(newList);
    } finally {
      setShowAddModal(false);
      setClickCoordinates(null);
      setInjuryEndDate('');
    }
  };

  const updateInjury = async (injuryId, payload) => {
  if (!playerInfo?.id) return;
  try {
    await api.put(`/players/${playerInfo.id}/injuries/${injuryId}`, payload);
    await fetchInjuries(); // Rafraîchir la liste après modification
  } catch (err) {
    console.error('Erreur lors de la mise à jour de la blessure:', err);
    alert('Erreur lors de la mise à jour de la blessure');
  }
};

  const deleteInjury = async (injuryId) => {
    try {
      if (playerInfo?.id) {
        await api.delete(`/players/${playerInfo.id}/injuries/${injuryId}`);
        await fetchInjuries();
      }
    } catch (err) { console.debug(err);
      setInjuries(injuries.filter(inj => inj.id !== injuryId));
    }
  };


  if (loading) {
    return (
      <div className="bg-white/60 min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

    // Render a table where each player is a column and each row is a stat
  const StatTable = ({ rows, stats }) => {
    const players = stats;
    return (
      <div className="overflow-x-auto">
        <table className="w-full table-auto border-collapse">
          <thead>
            <tr>
              <th className="px-4 py-2 text-left"></th>
              {players.map((p, i) => (
                <th key={i} className="px-4 py-2 text-left">
                  <div className="text-xs text-gray-500">{p?.player_name ?? '-'}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-t">
                <td className="px-4 py-3 text-sm text-gray-600 font-medium">{r.label}</td>
                {players.map((p, i) => (
                  <td key={i} className="px-4 py-3">
                    <div className={`text-2xl font-bold ${r.color || ''}`}>{r.format ? r.format(p?.[r.key]) : (p?.[r.key] ?? '-')}</div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };;

  // Render a single metric row with label + 1 or 2 values
  const StatRow = ({ label, value1, value2, color = 'text-gray-900' }) => (
    <div className="flex items-center justify-between border-t py-2 px-1">
      <span className="text-sm text-gray-600 font-medium">{label}</span>
      <div className="flex gap-6">
        <span className={`text-sm font-bold ${color}`}>{value1}</span>
        {value2 !== undefined && (
          <span className="text-sm font-bold text-orange-500">{value2}</span>
        )}
      </div>
    </div>
  );


  const formatVeoMetricValue = (value) => {
    if (value === null || value === undefined) {
      return '-';
    }
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return '-';
    }
    return Number.isInteger(numericValue) ? String(numericValue) : numericValue.toFixed(1);
  };

  const veoMetricMap = (veoStats?.metrics ?? []).reduce((acc, metric) => {
    acc[metric.slug] = metric.value;
    return acc;
  }, {});

  const handleShowPasswordForm = () => {
    setShowPasswordForm(true);
    setTimeout(() => {
      passwordFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      alert("Les nouveaux mots de passe ne correspondent pas.");
      return;
    }
    try {
      await api.put('/auth/me', { password: newPassword, old_password: oldPassword });
      alert("Mot de passe modifié avec succès !");
      setShowPasswordForm(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      alert("Erreur lors du changement de mot de passe : " + (err.response?.data?.detail || err.message));
    }
  };

  const me = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;

  const handleVeoCompare = async () => {
    if (
      !selectedVeoPlayer ||
      compareVeoStatsList.some(cs => cs?.player_name === selectedVeoPlayer)
    ) return;
    try {
      // Ajoute un état de loading si besoin
      const stats = await veoService.getPlayerMetricsSummaryByName(selectedVeoPlayer);
      setCompareVeoStatsList(prev => [...prev, stats]);
      setSelectedVeoPlayer('');
    } catch {
      alert("Erreur lors de la comparaison VEO");
    }
  };

  const clearVeoComparison = () => {
    setCompareVeoStatsList([]);
    setSelectedVeoPlayer('');
  };

  function PlayerComparisonSelector({
    filter,
    setFilter,
    selectedPlayer,
    setSelectedPlayer,
    allPlayers,
    allPlayersInfo,
    playerName,
    playerInfo,
    comparedList,
    onAdd,
    onClear,
    loading,
    label = "Comparer avec d'autres joueurs"
  }) {
    // Fonctions de filtrage
    const getAllPlayersList = () =>
      allPlayers.filter(name => name !== playerName && !comparedList.some(cs => cs?.player_name === name || cs === name));

    const getSamePositionPlayers = () => {
      if (!playerInfo?.position) return [];
      return allPlayers
        .filter(name => name !== playerName && !comparedList.some(cs => cs?.player_name === name || cs === name))
        .filter(name => {
          const info = allPlayersInfo.find(p => p.player_name === name);
          return info && info.position === playerInfo.position;
        });
    };

    const filteredPlayers = filter === 'all' ? getAllPlayersList() : getSamePositionPlayers();

    return (
      <div className="bg-gray-50/50 rounded-lg p-2 mb-4 pl-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">{label}</h2>
        <div className="flex gap-2 mb-2">
          <button
            className={`px-3 py-1 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            onClick={() => setFilter('all')}
          >
            Tous les joueurs
          </button>
          <button
            className={`px-3 py-1 rounded ${filter === 'samePosition' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
            onClick={() => setFilter('samePosition')}
          >
            Même poste {playerInfo?.position && `(${playerInfo.position})`}
          </button>
        </div>
        <div className="flex gap-4 mb-4">
          <select
            value={selectedPlayer}
            onChange={e => setSelectedPlayer(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">-- Choisir un joueur --</option>
            {filteredPlayers.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <button
            onClick={onAdd}
            disabled={!selectedPlayer || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
          >
            Ajouter à la comparaison
          </button>
          {comparedList.length > 0 && (
            <button
              onClick={onClear}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Effacer
            </button>
          )}
        </div>
      </div>
    );
  }

  const ComparisonBlock = () => (
    <div className="space-y-6">
      <div className="bg-gray-50/50 rounded-lg pt-2 pr-6">
        <label className="block mb-5 font-medium text-xl">Sélectionnez la meilleure session du joueur</label>
        <select
          value={selectedSession || ''}
          onChange={e => setSelectedSession(e.target.value)}
          className="mb-4 px-4 py-2 border rounded"
        >
          <option value="">-- Choisir une session --</option>
          {playerSessions.map(session => (
            <option key={session.id} value={session.id}>
              {session.title} ({new Date(session.date).toLocaleDateString()})
            </option>
          ))}
        </select>
        <button
          onClick={async () => {
            if (selectedSession) {
              await catapultService.setSelectedSession(playerName, selectedSession);
              alert("Session enregistrée !");
            }
          }}
          className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          disabled={!selectedSession}
        >
          Enregistrer
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-4">
          <h1 className="inline-block bg-white/50 px-4 py-2 rounded-md text-4xl font-bold text-black">
            {playerName}
          </h1>
          <p className="justify-self-center bg-white/50 px-4 py-2 rounded-md text-l font-bold text-black">{playerInfo?.role || 'Joueur'}</p>
        </div>

        <div className="bg-white/80 rounded-lg shadow-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex justify-center -mb-px">
              <button
                onClick={() => setActiveTab('info')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'info'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Info Player
              </button>

              <button
                onClick={() => setActiveTab('catapult')}
                className={`px- py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'catapult'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover;border-gray-300'
                }`}
              >
                Stats Catapult
              </button>

              <button
                onClick={() => setActiveTab('veo')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'veo'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Stats VEO
              </button>
              
              <button
                onClick={() => setActiveTab('medical')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'medical'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover;border-gray-300'
                }`}
              >
                Médical
              </button>
            </nav>
          </div>

          <div className="p-10">
            {activeTab === 'info' && (
              <div className="space-y-6">
                <div className="flex items-start gap-15">
                  <div className="flex-shrink-0">
                    <div className="relative w-48 h-48">
                      {playerInfo?.photo_url ? (
                        <img src={playerInfo.photo_url.startsWith('http') ? playerInfo.photo_url : `/api/physical${playerInfo.photo_url}`} alt="photo" className="w-48 h-48 object-cover rounded-lg" />
                      ) : (
                        <div className="w-48 h-48 bg-gray-200 rounded-lg flex items-center justify-center">
                          <svg className="w-24 h-24 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                          </svg>
                        </div>
                      )}

                      <input id="photo-upload" type="file" accept="image/*" onChange={handlePhotoSelect} className="hidden" />

                      <label htmlFor="photo-upload" className="absolute inset-0 flex items-center justify-center rounded-lg cursor-pointer hover:bg-black hover:bg-opacity-25">
                        {!playerInfo?.photo_url && (
                          <span className="px-3 py-1 bg-white bg-opacity-80 text-sm rounded">Upload</span>
                        )}
                      </label>


                    </div>
                  </div>

                  <div className="flex-1 grid grid-cols-2">
                    <div className="col-span-2 flex justify-end items-start">
                      <button
                        onClick={() => { setEditForm(playerInfo || {}); setShowEditModal(true); }}
                        className="ml-auto px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-900"
                      >
                        Modifier
                      </button>

                    </div>
                    <div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Nom complet</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.full_name || 'N/A'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Email</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.email || 'N/A'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Date de naissance</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.date_of_birth ? new Date(playerInfo.date_of_birth).toLocaleDateString() : 'À renseigner'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Âge</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.age ? `${playerInfo.age} ans` : 'N/A'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Adresse postale</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4 whitespace-pre-wrap break-words">{playerInfo?.adress || 'À renseigner'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">N° de téléphone</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.phone_number || 'À renseigner'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Personne à contacter</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.emergency_contact || 'À renseigner'}</p>
                      </div>
                    </div>

                    <div>
                      <div>
                        <label className="block text-sm font-medium text-gray-500">Poste</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.position || 'N/A'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Taille</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.height ? `${playerInfo.height} m` : 'À renseigner'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Poids</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.weight ? `${playerInfo.weight} kg` : 'À renseigner'}</p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-500">Pied fort</label>
                        <p className="text-lg font-semibold text-gray-900 mb-4">{playerInfo?.strong_foot || 'À renseigner'}</p>
                      </div>
                    </div>
                  </div>

                  </div>
                </div>
              )}

            {showEditModal && editForm && (
                  <div className="fixed inset-0 bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
                    <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 my-8" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
                      <h2 className="text-xl font-semibold mb-4">Modifier le joueur</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                        {me && playerInfo?.id === me.id && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700">Mot de passe</label>
                            <button
                              className="mb-4 px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                              onClick={handleShowPasswordForm}
                            >
                              Modifier le mot de passe
                            </button>
                            {showPasswordForm && (
                              <form
                                style={{ maxHeight: '320px', overflowY: 'auto' }}
                                ref={passwordFormRef}
                                className="mb-2 p-2 bg-gray-50 rounded border flex flex-col gap-2 max-w-xs max-h-80 overflow-y-auto"
                                onSubmit={handlePasswordChange}
                              >
                                <label>
                                  Ancien mot de passe
                                  <input
                                    type="password"
                                    className="w-full mt-1 px-2 py-1 border rounded"
                                    value={oldPassword}
                                    onChange={e => setOldPassword(e.target.value)}
                                    required
                                  />
                                </label>
                                <label>
                                  Nouveau mot de passe
                                  <input
                                    type="password"
                                    className="w-full mt-1 px-2 py-1 border rounded"
                                    value={newPassword}
                                    onChange={e => setNewPassword(e.target.value)}
                                    required
                                  />
                                </label>
                                <label>
                                  Confirmer le nouveau mot de passe
                                  <input
                                    type="password"
                                    className="w-full mt-1 px-2 py-1 border rounded"
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    required
                                  />
                                </label>
                                <div className="flex gap-2">
                                  <button
                                    type="submit"
                                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                                  >
                                    Enregistrer
                                  </button>
                                  <button
                                    type="button"
                                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                                    onClick={() => setShowPasswordForm(false)}
                                  >
                                    Annuler
                                  </button>
                                </div>
                              </form>
                            )}
                          </div>
                        )}

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Nom complet</label>
                          <input value={editForm.full_name || ''} onChange={(e)=>setEditForm({...editForm, full_name: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Email</label>
                          <input value={editForm.email || ''} onChange={(e)=>setEditForm({...editForm, email: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700">Poste</label>
                            <select
                              value={editForm.position || 'player'}
                              onChange={(e) => setEditForm({...editForm, position: e.target.value})}
                              className="mt-1 w-full px-3 py-2 border rounded"
                            >
                              <option value="ATTAQUANT">ATTAQUANT</option>
                              <option value="MILIEU">MILIEU</option>
                              <option value="DEFENSEUR CENTRAL">DEFENSEUR CENTRAL</option>
                              <option value="LATERAL">LATERAL</option>
                              <option value="AILIER">AILIER</option>
                            </select>
                          </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Date de naissance</label>
                          <input type="date" value={editForm.date_of_birth ? String(editForm.date_of_birth).split('T')[0] : ''} onChange={(e)=>setEditForm({...editForm, date_of_birth: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Âge</label>
                          <input type="number" value={editForm.age || ''} onChange={(e)=>setEditForm({...editForm, age: e.target.value ? parseInt(e.target.value,10) : null})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Adresse</label>
                          <textarea rows={2} value={editForm.adress || ''} onChange={(e)=>setEditForm({...editForm, adress: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded resize-none"></textarea>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">N° de téléphone</label>
                          <input value={editForm.phone_number || ''} onChange={(e)=>setEditForm({...editForm, phone_number: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Taille (m)</label>
                          <input type="number" step="0.01" value={editForm.height || ''} onChange={(e)=>setEditForm({...editForm, height: e.target.value ? parseFloat(e.target.value) : null})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Poids (kg)</label>
                          <input type="number" step="0.1" value={editForm.weight || ''} onChange={(e)=>setEditForm({...editForm, weight: e.target.value ? parseFloat(e.target.value) : null})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Pied fort</label>
                          <input value={editForm.strong_foot || ''} onChange={(e)=>setEditForm({...editForm, strong_foot: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700">Contact urgence</label>
                          <input value={editForm.emergency_contact || ''} onChange={(e)=>setEditForm({...editForm, emergency_contact: e.target.value})} className="mt-1 w-full px-3 py-2 border rounded" />
                        </div>

                        <div className="md:col-span-2 border-t pt-4 mt-2 grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="flex items-center gap-2">
                            <input
                              id="edit-is-active"
                              type="checkbox"
                              checked={editForm.is_active !== false}
                              onChange={(e) => setEditForm({...editForm, is_active: e.target.checked})}
                              className="h-4 w-4 rounded border-gray-300 text-blue-600"
                            />
                            <label htmlFor="edit-is-active" className="text-sm font-medium text-gray-700">Compte actif</label>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700">Rôle</label>
                            <select
                              value={editForm.role || 'player'}
                              onChange={(e) => setEditForm({...editForm, role: e.target.value})}
                              className="mt-1 w-full px-2 py-2 border rounded">
                              <option value="admin">Admin</option>
                              <option value="coach">Coach</option>
                              <option value="player">Joueur</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700">Équipe</label>
                            <select
                              value={editForm.team_id || ''}
                              onChange={(e) => setEditForm({...editForm, team_id: e.target.value ? parseInt(e.target.value,10) : null})}
                              className="mt-1 w-full px-2 py-2 border rounded">
                              <option value="">— Aucune —</option>
                              {teams.map(t => (
                                <option key={t.id} value={t.id}>
                                  {`${t.academy?.country?.name || 'unknown'}/${t.academy?.name || 'academy'}/${t.name}`}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>

                      </div>

                      <div className="flex justify-end gap-3 mt-6">
                        <button
                          onClick={() => { setShowEditModal(false); setEditForm(null); }}
                          className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                        >
                          Annuler
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              const updateData = {
                                email: editForm.email,
                                full_name: editForm.full_name,
                                role: editForm.role,
                                is_active: editForm.is_active !== false,
                                player_name: editForm.player_name,
                                age: editForm.age || null,
                                team_id: editForm.team_id || null,
                                position: editForm.position,
                                date_of_birth: editForm.date_of_birth || null,
                                adress: editForm.adress || null,
                                height: editForm.height || null,
                                weight: editForm.weight || null,
                                strong_foot: editForm.strong_foot || null,
                                phone_number: editForm.phone_number || null,
                                emergency_contact: editForm.emergency_contact || null,
                              };
                              if (editForm.password && editForm.password.trim() !== '') {
                                updateData.password = editForm.password;
                              }
                              const res = await api.put(`/auth/users/${playerInfo?.id}`, updateData);
                              setPlayerInfo(res.data);
                              const me = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;
                              if (me && me.id === res.data.id) { localStorage.setItem('user', JSON.stringify(res.data)); }
                              setShowEditModal(false);
                              setEditForm(null);
                            } catch(err) {
                              console.error(err);
                              alert('Erreur lors de la sauvegarde: ' + (err.response?.data?.detail || err.message));
                            }
                          }}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Enregistrer
                        </button>
                      </div>
                    </div>
                  </div>
                )}

            {activeTab === 'catapult' && playerStats && (
              <>
                <div className="grid grid-cols-2 gap-6 mb-6">
                  <div className="text-right">
                    <ComparisonBlock />
                  </div>
                  <div>
                    <PlayerComparisonSelector
                      filter={catapultFilter}
                      setFilter={setCatapultFilter}
                      selectedPlayer={selectedPlayer}
                      setSelectedPlayer={setSelectedPlayer}
                      allPlayers={allPlayers}
                      allPlayersInfo={allPlayersInfo}
                      playerName={playerName}
                      playerInfo={playerInfo}
                      comparedList={comparePlayers}
                      onAdd={handleCompare}
                      onClear={clearComparison}
                      loading={false}
                      label="Comparer Catapult avec d'autres joueurs"
                    />
                  </div>
                </div>
                <div className="bg-white/50 rounded-lg border p-6 space-y-6">
                  <StatTable
                    rows={[
                      { key: 'minutes', label: 'Minutes', format: v => Math.round(v), color: 'text-blue-600' },
                      { key: 'distance', label: 'Distance (m)', format: v => v?.toFixed(0), color: 'text-green-600' },
                      { key: 'hsr', label: 'HSR (m)', format: v => v?.toFixed(0), color: 'text-orange-600' },
                      { key: 'sprint', label: 'Sprint (m)', format: v => v?.toFixed(0), color: 'text-red-600' },
                      { key: 'vmax', label: 'Vmax (km/h)', format: v => v?.toFixed(1), color: 'text-purple-600' },
                      { key: 'dec', label: 'DEC', format: v => v?.toFixed(0), color: 'text-purple-600' },
                      { key: 'pp', label: 'PP', format: v => v?.toFixed(0), color: 'text-indigo-600' },
                      { key: 'm/min', label: 'M/MIN', format: v => v?.toFixed(1), color: 'text-green-600' },
                    ]}
                    stats={[selectedSessionStats, ...comparePlayersStats]}
                  />
                </div>
              </>
            )}

            {activeTab === 'veo' && (
              <>
                <div className="flex justify-center">
                  <div className="w-full max-w-md">
                    <PlayerComparisonSelector
                      filter={veoFilter}
                      setFilter={setVeoFilter}
                      selectedPlayer={selectedVeoPlayer}
                      setSelectedPlayer={setSelectedVeoPlayer}
                      allPlayers={allPlayers}
                      allPlayersInfo={allPlayersInfo}
                      playerName={playerName}
                      playerInfo={playerInfo}
                      comparedList={compareVeoStatsList}
                      onAdd={handleVeoCompare}
                      onClear={clearVeoComparison}
                      loading={loading}
                      label="Comparer VEO avec d'autres joueurs"
                    />
                  </div>
                </div>
                <div className="bg-white/50 rounded-lg border p-6 space-y-6">
                  <h2 className="text-2xl font-bold text-gray-900">Metriques VEO (moyenne par session)</h2>
                  {veoLoading ? (
                    <p className="text-gray-500 text-sm">Chargement des metriques VEO...</p>
                  ) : !veoStats ? (
                    <p className="text-gray-500 text-sm">
                      Aucune metrique VEO disponible pour ce joueur sur les sessions disponibles.
                    </p>
                  ) : (
                    <>
                      <div className="overflow-x-auto">
                        <table className="w-full table-auto border-collapse">
                          <thead>
                            <tr>
                              <th className="px-4 py-2 text-left text-sm text-gray-600 font-medium">Métrique</th>
                              <th className="px-4 py-2 text-left">
                                <div className="text-xs text-gray-500">{veoStats.player_name || playerName}</div>
                                <div className="text-xs text-gray-400">{veoStats.sessions_count} session(s)</div>
                              </th>
                              {compareVeoStatsList.map((cs, i) => (
                                <th key={i} className="px-4 py-2 text-left">
                                  <div className="text-xs text-gray-500">{cs?.player_name || comparePlayers[i]}</div>
                                  <div className="text-xs text-gray-400">{cs?.sessions_count ?? 0} session(s)</div>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {VEO_PLAYER_METRIC_ORDER.map((slug) => (
                              <tr key={slug} className="border-t">
                                <td className="px-4 py-3 text-sm text-gray-600 font-medium">
                                  {VEO_PLAYER_METRIC_LABELS[slug] || slug}
                                </td>
                                <td className="px-4 py-3 text-sm font-bold text-gray-900">
                                  {formatVeoMetricValue(veoMetricMap[slug])}
                                </td>
                                {compareVeoStatsList.map((cs, i) => {
                                  // On crée un mapping pour chaque joueur comparé
                                  const csMetricMap = (cs?.metrics ?? []).reduce((acc, metric) => {
                                    acc[metric.slug] = metric.value;
                                    return acc;
                                  }, {});
                                  return (
                                    <td key={i} className="px-4 py-3 text-sm font-bold text-gray-900">
                                      {formatVeoMetricValue(csMetricMap[slug])}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              </>
            )}

            {activeTab === 'medical' && (
              <div className="space-y-6">
                <MedicalMap
                  injuries={injuries}
                  onCoordinatesClick={onCoordinatesClick}
                  onDeleteInjury={deleteInjury}
                  onEditInjury={(injury) => {
                    setEditInjuryForm(injury);
                    setShowEditInjuryModal(true);
                    setInjuryDate(injury.injury_date || '');
                    setInjuryEndDate(injury.injury_end_date || '');
                    setRestrictionDate(injury.restriction_date || '');
                    setRestrictionType(injury.restriction_type || 'no_sport');
                    setInjuryComment(injury.comment || '');
                    setClickCoordinates({ coord_x: injury.coord_x, coord_y: injury.coord_y });
                  }}
                />

                {showAddModal && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black opacity-40" onClick={() => setShowAddModal(false)}></div>
                    <div className="bg-white rounded-lg shadow-lg z-60 p-6 w-full max-w-170">
                      <h3 className="text-xl font-semibold mb-4">Ajouter une blessure</h3>
                      {clickCoordinates && (
                        <div className="mb-3 text-sm text-gray-600">
                          Position: {clickCoordinates.coord_x.toFixed(1)}%, {clickCoordinates.coord_y.toFixed(1)}%
                        </div>
                      )}
                      <label className="block text-m font-medium text-gray-700">Date de la blessure</label>
                      <input 
                        type="date" 
                        value={injuryDate} 
                        onChange={(e) => setInjuryDate(e.target.value)} 
                        className="mt-1 mb-3 w-full px-3 py-2 border rounded" 
                      />
                      <label className="block text-m font-medium text-gray-700">En arrêt jusqu'au</label>
                      <input 
                        type="date" 
                        value={injuryEndDate} 
                        onChange={(e) => setInjuryEndDate(e.target.value)} 
                        className="mt-1 mb-3 w-full px-3 py-2 border rounded" 
                      />
                      <label className="mt-2 block text-m font-medium text-gray-700">Que permet cette blessure</label>
                      <div className="flex items-center gap-2 mt-2">
                        <span>Jusqu'au</span>
                        <input
                          type="date"
                          value={restrictionDate}
                          onChange={e => setRestrictionDate(e.target.value)}
                          className="px-2 py-1 border rounded"
                        />
                        <span>Le joueur</span>
                        <select
                          value={restrictionType}
                          onChange={e => setRestrictionType(e.target.value)}
                          className="px-2 py-1 border rounded"
                        >
                          <option value="no_sport">Ne peut pas faire d'activité sportive</option>
                          <option value="light_training">Peut s'entrainer sans forcer</option>
                          <option value="normal_play">Peut jouer normalement</option>
                        </select>
                      </div>
                      <label className="mt-4 block text-sm font-medium text-gray-700">Commentaire (localisation, type...)</label>
                      <textarea 
                        value={injuryComment} 
                        onChange={(e) => setInjuryComment(e.target.value)} 
                        placeholder="Ex: Genou droit, entorse légère"
                        className="mt-1 mb-4 w-full px-3 py-2 border rounded" 
                        rows={3}
                      ></textarea>
                      <div className="flex justify-end gap-3">
                        <button 
                          onClick={() => { setShowAddModal(false); setInjuryEndDate(''); }} 
                          className="px-4 py-2 rounded border hover:bg-gray-50"
                        >
                          Annuler
                        </button>
                        <button 
                          onClick={addInjury} 
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Ajouter
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {showEditInjuryModal && editInjuryForm && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="bg-white rounded-lg p-6 w-full max-w-170 mx-4 my-8">
                      <h3 className="text-lg font-semibold mb-4">Modifier la blessure</h3>
                      <label className="block text-sm font-medium text-gray-700">Date de la blessure</label>
                      <input
                        type="date"
                        value={injuryDate}
                        onChange={(e) => setInjuryDate(e.target.value)}
                        className="mt-1 mb-3 w-full px-3 py-2 border rounded"
                      />
                      <label className="block text-sm font-medium text-gray-700">En arrêt jusqu'au</label>
                      <input
                        type="date"
                        value={injuryEndDate}
                        onChange={(e) => setInjuryEndDate(e.target.value)}
                        className="mt-1 mb-3 w-full px-3 py-2 border rounded"
                      />
                      <label className="mt-2 block text-m font-medium text-gray-700">Que permet cette blessure</label>
                      <div className="flex items-center gap-2 mt-2">
                        <span>Jusqu'au</span>
                        <input
                          type="date"
                          value={restrictionDate}
                          onChange={e => setRestrictionDate(e.target.value)}
                          className="px-2 py-1 border rounded"
                        />
                        <span>Le joueur</span>
                        <select
                          value={restrictionType}
                          onChange={e => setRestrictionType(e.target.value)}
                          className="px-2 py-1 border rounded"
                        >
                          <option value="no_sport">Ne peut pas faire d'activité sportive</option>
                          <option value="light_training">Peut s'entrainer sans forcer</option>
                          <option value="normal_play">Peut jouer normalement</option>
                        </select>
                      </div>
                      <label className="block text-sm font-medium text-gray-700">Commentaire</label>
                      <textarea
                        value={injuryComment}
                        onChange={(e) => setInjuryComment(e.target.value)}
                        className="mt-1 mb-4 w-full px-3 py-2 border rounded"
                        rows={3}
                      />
                      <div className="flex justify-end gap-3">
                        <button
                          onClick={() => { setShowEditInjuryModal(false); setEditInjuryForm(null); }}
                          className="px-4 py-2 rounded border hover:bg-gray-50"
                        >
                          Annuler
                        </button>
                        <button
                          onClick={async () => {
                            await updateInjury(editInjuryForm.id, {
                              injury_date: injuryDate,
                              injury_end_date: injuryEndDate,
                              comment: injuryComment,
                              coord_x: clickCoordinates?.coord_x,
                              coord_y: clickCoordinates?.coord_y,
                              restriction_date: restrictionDate,
                              restriction_type: restrictionType
                            });
                            setShowEditInjuryModal(false);
                            setEditInjuryForm(null);
                          }}
                          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                          Enregistrer
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
