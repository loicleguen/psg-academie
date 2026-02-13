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
  const [comparePlayerStats, setComparePlayerStats] = useState(null);
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');

  // Medical state
  const [injuries, setInjuries] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [clickCoordinates, setClickCoordinates] = useState(null);
  const [injuryDate, setInjuryDate] = useState('');
  const [injuryComment, setInjuryComment] = useState('');

  useEffect(() => {
    loadPlayerInfo();
    loadPlayerStats();
    loadAllPlayers();
  }, [playerName]);

  useEffect(() => {
    if (compareWith && activeTab === 'stats') {
      loadComparePlayerStats(compareWith);
    } else {
      setComparePlayerStats(null);
    }
  }, [compareWith, activeTab]);

  useEffect(() => {
    if (activeTab === 'medical') {
      fetchInjuries();
    }
  }, [activeTab, playerInfo]);

  const loadPlayerInfo = async () => {
    try {
      const response = await api.get('/auth/users');
      const player = response.data.find(u => u.player_name === playerName || u.full_name === playerName);
      setPlayerInfo(player);
    } catch (error) {
      console.error('Erreur chargement info joueur:', error);
    }
  };

  const loadPlayerStats = async () => {
    try {
      setLoading(true);
      const stats = await catapultService.getPlayerStats(playerName);
      setPlayerStats(stats);
    } catch (error) {
      console.error('Erreur chargement stats joueur:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadComparePlayerStats = async (name) => {
    try {
      const stats = await catapultService.getPlayerStats(name);
      setComparePlayerStats(stats);
    } catch (error) {
      console.error('Erreur chargement stats comparaison:', error);
    }
  };

  const loadAllPlayers = async () => {
    try {
      const players = await catapultService.getAllPlayers();
      setAllPlayers(players);
    } catch (error) {
      console.error('Erreur chargement joueurs:', error);
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

  const handleCompare = () => {
    if (selectedPlayer && selectedPlayer !== playerName) {
      setSearchParams({ compare: selectedPlayer });
    }
  };

  const clearComparison = () => {
    setSelectedPlayer('');
    setSearchParams({});
  };

  const getFilteredPlayers = () => {
    if (!playerInfo?.position) return allPlayers.filter(name => name !== playerName);
    return allPlayers.filter(name => {
      if (name === playerName) return false;
      return true;
    });
  };

  const onCoordinatesClick = (coords) => {
    setClickCoordinates(coords);
    setInjuryDate('');
    setInjuryComment('');
    setShowAddModal(true);
  };

  const addInjury = async () => {
    if (!clickCoordinates) return;
    
    const payload = {
      coord_x: clickCoordinates.coord_x,
      coord_y: clickCoordinates.coord_y,
      injury_date: injuryDate || new Date().toISOString().slice(0,10),
      comment: injuryComment || ''
    };

    try {
      if (playerInfo?.id) {
        await api.post(`/players/${playerInfo.id}/injuries`, payload);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const StatRow = ({ label, value1, value2, color }) => (
    <div className="border-b pb-4">
      <p className="text-sm text-gray-600 font-medium mb-2">{label}</p>
      <div className={comparePlayerStats ? "grid grid-cols-2 gap-4" : "flex"}>
        <div>
          <p className="text-xs text-gray-500 mb-1">{playerStats?.player_name}</p>
          <p className={`text-2xl font-bold ${color}`}>{value1}</p>
        </div>
        {comparePlayerStats && (
          <div>
            <p className="text-xs text-gray-500 mb-1">{comparePlayerStats.player_name}</p>
            <p className={`text-2xl font-bold ${color}`}>{value2}</p>
          </div>
        )}
      </div>
    </div>
  );

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
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'stats'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Stats Catapult
              </button>
              <button
                onClick={() => setActiveTab('medical')}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'medical'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
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
                    <div className="w-48 h-48 bg-gray-200 rounded-lg flex items-center justify-center">
                      <svg className="w-24 h-24 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <p className="text-sm text-gray-500 mt-2 text-center">Photo à venir</p>
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
                  <div className="flex gap-4 items-end">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Sélectionner un joueur {playerInfo?.position && `(${playerInfo.position})`}
                      </label>
                      <select
                        value={selectedPlayer}
                        onChange={(e) => setSelectedPlayer(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">-- Choisir un joueur --</option>
                        {getFilteredPlayers().map(name => (
                          <option key={name} value={name}>{name}</option>
                        ))}
                      </select>
                    </div>
                    <button
                      onClick={handleCompare}
                      disabled={!selectedPlayer}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Comparer
                    </button>
                    {comparePlayerStats && (
                      <button
                        onClick={clearComparison}
                        className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                      >
                        Effacer
                      </button>
                    )}
                  </div>
                </div>

                <div className="bg-white rounded-lg border p-6 space-y-6">
                  <div className="border-b pb-3">
                    <p className="text-sm text-gray-600 font-medium mb-2">Nombre de sessions</p>
                    <div className={comparePlayerStats ? "grid grid-cols-2 gap-4" : "flex"}>
                      <div>
                        <p className="text-xs text-gray-500 mb-1">{playerStats.player_name}</p>
                        <p className="text-2xl font-bold text-blue-600">{playerStats.sessions_count}</p>
                      </div>
                      {comparePlayerStats && (
                        <div>
                          <p className="text-xs text-gray-500 mb-1">{comparePlayerStats.player_name}</p>
                          <p className="text-2xl font-bold text-blue-600">{comparePlayerStats.sessions_count}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <StatRow label="Vitesse Max (m/s)" value1={playerStats.vitesse_max?.toFixed(2)} value2={comparePlayerStats?.vitesse_max?.toFixed(2)} color="text-gray-900" />
                  <StatRow label="Vitesse Moyenne (m/s)" value1={playerStats.vitesse_avg?.toFixed(2)} value2={comparePlayerStats?.vitesse_avg?.toFixed(2)} color="text-gray-900" />
                  <StatRow label="HSR Max (m)" value1={playerStats.hsr_max?.toFixed(0)} value2={comparePlayerStats?.hsr_max?.toFixed(0)} color="text-orange-600" />
                  <StatRow label="HSR Moyen (m)" value1={playerStats.hsr_avg?.toFixed(0)} value2={comparePlayerStats?.hsr_avg?.toFixed(0)} color="text-orange-600" />
                  <StatRow label="Sprint Max (m)" value1={playerStats.sprint_max?.toFixed(0)} value2={comparePlayerStats?.sprint_max?.toFixed(0)} color="text-red-600" />
                  <StatRow label="Sprint Moyen (m)" value1={playerStats.sprint_avg?.toFixed(0)} value2={comparePlayerStats?.sprint_avg?.toFixed(0)} color="text-red-600" />
                  <StatRow label="Distance Max (m)" value1={playerStats.distance_max?.toFixed(0)} value2={comparePlayerStats?.distance_max?.toFixed(0)} color="text-green-600" />
                  <StatRow label="Distance Moyenne (m)" value1={playerStats.distance_avg?.toFixed(0)} value2={comparePlayerStats?.distance_avg?.toFixed(0)} color="text-green-600" />
                  <StatRow label="DEC Max" value1={playerStats.dec_max?.toFixed(0)} value2={comparePlayerStats?.dec_max?.toFixed(0)} color="text-purple-600" />
                  <StatRow label="DEC Moyen" value1={playerStats.dec_avg?.toFixed(0)} value2={comparePlayerStats?.dec_avg?.toFixed(0)} color="text-purple-600" />
                  <StatRow label="PP Max" value1={playerStats.pp_max?.toFixed(2)} value2={comparePlayerStats?.pp_max?.toFixed(2)} color="text-indigo-600" />
                  <StatRow label="PP Moyen" value1={playerStats.pp_avg?.toFixed(2)} value2={comparePlayerStats?.pp_avg?.toFixed(2)} color="text-indigo-600" />
                </div>
              </div>
            )}

            {activeTab === 'medical' && (
              <div className="space-y-6">
                <MedicalMap
                  injuries={injuries}
                  onCoordinatesClick={onCoordinatesClick}
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
