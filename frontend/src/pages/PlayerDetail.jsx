import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
import api from '../services/api';
import MedicalMap from '../components/MedicalMap';

export default function PlayerDetail() {
  const { playerName } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const compareWith = searchParams.get('compare');

  const [activeTab, setActiveTab] = useState('info');
  const [playerInfo, setPlayerInfo] = useState(null);
  const [playerStats, setPlayerStats] = useState(null);
  const [comparePlayers, setComparePlayers] = useState([]);
  const [comparePlayersStats, setComparePlayersStats] = useState([]);
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [allPlayersInfo, setAllPlayersInfo] = useState([]);

    // Medical state
  const [injuries, setInjuries] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [clickCoordinates, setClickCoordinates] = useState(null);
  const [injuryDate, setInjuryDate] = useState('');
  const [injuryComment, setInjuryComment] = useState('');

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
        } catch (e) {}
      } else {
        try { await loadPlayerInfo(); } catch(e) {}
      }

    } catch (err) {
      console.error('Upload failed', err);
    }
  };


  useEffect(() => {
    loadPlayerInfo();
    loadPlayerStats();
    loadAllPlayers();
    loadAllPlayersInfo();
  }, [playerName]);

  useEffect(() => {
    if (compareWith && activeTab === 'stats') {
      setComparePlayers([compareWith]);
      (async () => {
        try {
          const s = await catapultService.getPlayerStats(compareWith);
          setComparePlayersStats([s]);
        } catch (e) {
          setComparePlayersStats([]);
        }
      })();
    } else if (activeTab !== 'stats') {
      setComparePlayers([]);
      setComparePlayersStats([]);
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
        } catch (e) {
        }
      }

      try {
        const meRes = await api.get('/auth/me');
        const me = meRes.data;
        if (me && (me.player_name === playerName || me.full_name === playerName)) {
          setPlayerInfo(me);
          return;
        }
      } catch (e) {}

      const response = await api.get('/auth/users');
      const player = response.data.find(u => u.player_name === playerName || u.full_name === playerName);
      setPlayerInfo(player);
    } catch (error) {
    }
  };

  const loadPlayerStats = async () => {
    try {
      setLoading(true);
      const stats = await catapultService.getPlayerStats(playerName);
      setPlayerStats(stats);
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  const loadOneCompareStats = async (name) => {
    try {
      const stats = await catapultService.getPlayerStats(name);
      return stats;
    } catch (error) {
      return null;
    }
  };

  const loadAllPlayers = async () => {
    try {
      const players = await catapultService.getAllPlayers();
      setAllPlayers(players);
    } catch (error) {
    }
  };

  const loadAllPlayersInfo = async () => {
    try {
      const response = await api.get('/auth/users');
      setAllPlayersInfo(response.data.filter(u => u.player_name));
    } catch (error) {
    }
  };


  const fetchInjuries = async () => {
    if (!playerInfo) return;
    try {
      const res = await api.get(`/players/${playerInfo.id}/injuries`);
      const list = res.data || [];
      list.sort((a,b) => new Date(b.injury_date) - new Date(a.injury_date));
      setInjuries(list);
    } catch (err) {
      setInjuries([]);
    }
  };

  const handleCompare = async () => {
    if (!selectedPlayer || selectedPlayer === playerName) return;
    if (comparePlayers.includes(selectedPlayer)) return;
    if (comparePlayers.length >= 5) {
      alert('Maximum 5 joueurs comparés.');
      return;
    }
    setComparePlayers(prev => [...prev, selectedPlayer]);
    setSelectedPlayer('');
    try {
      const stats = await loadOneCompareStats(selectedPlayer);
      if (stats) {
        setComparePlayersStats(prev => [...prev, stats]);
      } else {
        setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
        alert('Impossible de charger les stats pour ' + selectedPlayer);
      }
    } catch (e) {
      setComparePlayers(prev => prev.filter(p => p !== selectedPlayer));
    }
  };

  const clearComparison = () => {
    setSelectedPlayer('');
    setComparePlayers([]);
    setComparePlayersStats([]);
    setSearchParams({});
  };

  const getAllPlayersList = () => {
    return allPlayers.filter(name => name !== playerName);
  };

  const getSamePositionPlayers = () => {
    if (!playerInfo?.position) return [];
    return allPlayersInfo
      .filter(p => p.position === playerInfo.position && p.player_name !== playerName)
      .map(p => p.player_name);
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
      comment: injuryComment || ''
    };


    try {
      if (playerInfo?.id) {
        const response = await api.post(`/players/${playerInfo.id}/injuries`, payload);
        await fetchInjuries();
      } else {
        throw new Error('no player id');
      }
    } catch (err) {
      const newList = [{ ...payload, created_at: new Date().toISOString() }, ...injuries];
      newList.sort((a,b) => new Date(b.injury_date) - new Date(a.injury_date));
      setInjuries(newList);
    } finally {
      setShowAddModal(false);
      setClickCoordinates(null);
    }
  };

  const deleteInjury = async (injuryId) => {
    try {
      if (playerInfo?.id) {
        await api.delete(`/players/${playerInfo.id}/injuries/${injuryId}`);
        await fetchInjuries();
      }
    } catch (err) {
      setInjuries(injuries.filter(inj => inj.id !== injuryId));
    }
  };


  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const StatRow = ({ label, values, color }) => {
    const cols = values.length;
    return (
      <div className="border-b pb-4">
        <p className="text-sm text-gray-600 font-medium mb-2">{label}</p>
        <div className={cols > 1 ? `grid grid-cols-${cols} gap-4` : 'flex'}>
          {values.map((v, idx) => (
            <div key={idx}>
              <p className="text-xs text-gray-500 mb-1">
                {idx === 0 ? playerStats?.player_name : comparePlayersStats[idx-1]?.player_name}
              </p>
              <p className={`text-2xl font-bold ${color}`}>{v ?? '-'}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <button 
          onClick={() => navigate(-1)} 
          className="mb-6 text-blue-600 hover:text-blue-800 flex items-center transition-colors"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Retour
        </button>

        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {playerName}
          </h1>
          <p className="text-gray-600">{playerInfo?.position || 'Joueur'}</p>
        </div>

        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
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
                onClick={() => setActiveTab('stats')}
                className={`px- py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'stats'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover;border-gray-300'
                }`}
              >
                Stats Catapult
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

          <div className="p-6">
            {activeTab === 'info' && (
              <div className="space-y-6">
                <div className="flex items-start gap-6">
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

                  <div className="flex-1 grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Nom complet</label>
                      <p className="text-lg font-semibold text-gray-900">{playerInfo?.full_name || 'N/A'}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Âge</label>
                      <p className="text-lg font-semibold text-gray-900">{playerInfo?.age ? `${playerInfo.age} ans` : 'N/A'}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Email</label>
                      <p className="text-lg font-semibold text-gray-900">{playerInfo?.email || 'N/A'}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Poste</label>
                      <p className="text-lg font-semibold text-gray-900">{playerInfo?.position || 'N/A'}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Adresse postale</label>
                      <p className="text-lg font-semibold text-gray-900">À renseigner</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-500 mb-1">Pied fort</label>
                      <p className="text-lg font-semibold text-gray-900">À renseigner</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'stats' && playerStats && (
              <div className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                    </svg>
                    <span className="font-semibold text-blue-900">Poste: {playerInfo?.position || 'Non défini'}</span>
                  </div>
                </div>

                <p className="text-gray-600">Données des 3 derniers mois</p>

                <div className="bg-gray-50 rounded-lg p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">Comparer avec un autre joueur</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Tous les joueurs
                      </label>
                      <select
                        value={selectedPlayer}
                        onChange={(e) => setSelectedPlayer(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">-- Choisir un joueur --</option>
                        {getAllPlayersList().map(name => (
                          <option key={name} value={name}>{name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Même poste {playerInfo?.position && `(${playerInfo.position})`}
                      </label>
                      <select
                        value={selectedPlayer}
                        onChange={(e) => setSelectedPlayer(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      >
                        <option value="">-- Choisir un joueur --</option>
                        {getSamePositionPlayers().map(name => (
                          <option key={name} value={name}>{name}</option>
                        ))}
                      </select>
                      {getSamePositionPlayers().length === 0 && playerInfo?.position && (
                        <p className="text-xs text-gray-500 mt-1">Aucun autre joueur au poste {playerInfo.position}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <button
                      onClick={handleCompare}
                      disabled={!selectedPlayer}
                      className="transform translate-x-[400px] px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Comparer
                    </button>
                    {comparePlayersStats.length > 0 && (
                      <button
                        onClick={clearComparison}
                        className="transform translate-x-[400px] px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                      >
                        Effacer
                      </button>
                    )}
                  </div>
                </div>

                <div className="bg-white rounded-lg border p-6 space-y-6">
                  <div className="border-b pb-3">
                    <p className="text-sm text-gray-600 font-medium mb-2">Nombre de sessions</p>
                    <div className={comparePlayersStats.length > 0 ? `grid grid-cols-${1 + comparePlayersStats.length} gap-4` : 'flex'}>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">{playerStats.player_name}</p>
                        <p className="text-2xl font-bold text-blue-600">{playerStats.sessions_count}</p>
                      </div>
                      {comparePlayersStats.map((s, idx) => (
                        <div key={idx}>
                          <p className="text-xs text-gray-500 mb-1">{s.player_name}</p>
                          <p className="text-2xl font-bold text-blue-600">{s.sessions_count}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <StatRow label="Vitesse Max (m/s)" values={[playerStats.vitesse_max?.toFixed(2), ...comparePlayersStats.map(s => s.vitesse_max?.toFixed(2))]} color="text-gray-900" />
                  <StatRow label="Vitesse Moyenne (m/s)" values={[playerStats.vitesse_avg?.toFixed(2), ...comparePlayersStats.map(s => s.vitesse_avg?.toFixed(2))]} color="text-gray-900" />
                  <StatRow label="HSR Max (m)" values={[playerStats.hsr_max?.toFixed(0), ...comparePlayersStats.map(s => s.hsr_max?.toFixed(0))]} color="text-orange-600" />
                  <StatRow label="HSR Moyen (m)" values={[playerStats.hsr_avg?.toFixed(0), ...comparePlayersStats.map(s => s.hsr_avg?.toFixed(0))]} color="text-orange-600" />
                  <StatRow label="Sprint Max (m)" values={[playerStats.sprint_max?.toFixed(0), ...comparePlayersStats.map(s => s.sprint_max?.toFixed(0))]} color="text-red-600" />
                  <StatRow label="Sprint Moyen (m)" values={[playerStats.sprint_avg?.toFixed(0), ...comparePlayersStats.map(s => s.sprint_avg?.toFixed(0))]} color="text-red-600" />
                  <StatRow label="Distance Max (m)" values={[playerStats.distance_max?.toFixed(0), ...comparePlayersStats.map(s => s.distance_max?.toFixed(0))]} color="text-green-600" />
                  <StatRow label="Distance Moyenne (m)" values={[playerStats.distance_avg?.toFixed(0), ...comparePlayersStats.map(s => s.distance_avg?.toFixed(0))]} color="text-green-600" />
                  <StatRow label="DEC Max" values={[playerStats.dec_max?.toFixed(0), ...comparePlayersStats.map(s => s.dec_max?.toFixed(0))]} color="text-purple-600" />
                  <StatRow label="DEC Moyen" values={[playerStats.dec_avg?.toFixed(0), ...comparePlayersStats.map(s => s.dec_avg?.toFixed(0))]} color="text-purple-600" />
                  <StatRow label="PP Max" values={[playerStats.pp_max?.toFixed(2), ...comparePlayersStats.map(s => s.pp_max?.toFixed(2))]} color="text-indigo-600" />
                  <StatRow label="PP Moyen" values={[playerStats.pp_avg?.toFixed(2), ...comparePlayersStats.map(s => s.pp_avg?.toFixed(2))]} color="text-indigo-600" />
                </div>
              </div>
            )}

            {activeTab === 'medical' && (
              <div className="space-y-6">
                <MedicalMap
                  injuries={injuries}
                  onCoordinatesClick={onCoordinatesClick}
                  onDeleteInjury={deleteInjury}
                />

                {showAddModal && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black opacity-40" onClick={() => setShowAddModal(false)}></div>
                    <div className="bg-white rounded-lg shadow-lg z-60 p-6 w-full max-w-md">
                      <h3 className="text-lg font-semibold mb-4">Ajouter une blessure</h3>
                      {clickCoordinates && (
                        <div className="mb-3 text-sm text-gray-600">
                          Position: {clickCoordinates.coord_x.toFixed(1)}%, {clickCoordinates.coord_y.toFixed(1)}%
                        </div>
                      )}
                      <label className="block text-sm font-medium text-gray-700">Date de la blessure</label>
                      <input 
                        type="date" 
                        value={injuryDate} 
                        onChange={(e) => setInjuryDate(e.target.value)} 
                        className="mt-1 mb-3 w-full px-3 py-2 border rounded" 
                      />
                      <label className="block text-sm font-medium text-gray-700">Commentaire (localisation, type...)</label>
                      <textarea 
                        value={injuryComment} 
                        onChange={(e) => setInjuryComment(e.target.value)} 
                        placeholder="Ex: Genou droit, entorse légère"
                        className="mt-1 mb-4 w-full px-3 py-2 border rounded" 
                        rows={3}
                      ></textarea>
                      <div className="flex justify-end gap-3">
                        <button 
                          onClick={() => setShowAddModal(false)} 
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

              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
