import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { catapultService } from '../services/catapultService';

export default function PlayerDetail() {
  const { playerName } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const compareWith = searchParams.get('compare');

  const [playerStats, setPlayerStats] = useState(null);
  const [comparePlayerStats, setComparePlayerStats] = useState(null);
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');

  useEffect(() => {
    loadPlayerStats();
    loadAllPlayers();
  }, [playerName]);

  useEffect(() => {
    if (compareWith) {
      loadComparePlayerStats(compareWith);
    } else {
      setComparePlayerStats(null);
    }
  }, [compareWith]);

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
      const sessions = await catapultService.getSessions();
      const uniquePlayers = [...new Set(sessions.map(s => s.player_name))].filter(Boolean);
      setAllPlayers(uniquePlayers);
    } catch (error) {
      console.error('Erreur chargement joueurs:', error);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!playerStats) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <button onClick={() => navigate(-1)} className="mb-4 text-blue-600 hover:text-blue-800 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Retour
          </button>
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-xl text-gray-600">Aucune donnée disponible pour ce joueur</p>
          </div>
        </div>
      </div>
    );
  }

  const StatCard = ({ title, stats, playerName }) => (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{playerName}</h3>
      <div className="space-y-3">
        {Object.entries(stats).map(([key, value]) => (
          <div key={key} className="flex justify-between items-center border-b pb-2">
            <span className="text-gray-600 font-medium">{title[key] || key}:</span>
            <span className="text-gray-900 font-bold">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );

  const statLabels = {
    sessions_count: 'Sessions',
    vitesse_max: 'Vitesse max (km/h)',
    vitesse_avg: 'Vitesse moyenne (km/h)',
    hsr_max: 'HSR max (m)',
    hsr_avg: 'HSR moyen (m)',
    sprint_max: 'Sprint max (m)',
    sprint_avg: 'Sprint moyen (m)',
    distance_max: 'Distance max (km)',
    distance_avg: 'Distance moyenne (km)',
    dec_max: 'Décélérations max',
    dec_avg: 'Décélérations moy',
    pp_max: 'Power Plays max',
    pp_avg: 'Power Plays moy'
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <button
          onClick={() => navigate(-1)}
          className="mb-6 text-blue-600 hover:text-blue-800 flex items-center"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Retour
        </button>

        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            {decodeURIComponent(playerName)}
          </h1>
          <p className="text-gray-600">Analyse sur les 3 derniers mois ({playerStats.sessions_count} sessions)</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Comparer avec un autre joueur</h2>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sélectionner un joueur
              </label>
              <select
                value={selectedPlayer}
                onChange={(e) => setSelectedPlayer(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Choisir un joueur --</option>
                {allPlayers
                  .filter(p => p !== playerName)
                  .map(player => (
                    <option key={player} value={player}>{player}</option>
                  ))
                }
              </select>
            </div>
            <button
              onClick={handleCompare}
              disabled={!selectedPlayer}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
            >
              Comparer
            </button>
            {compareWith && (
              <button
                onClick={clearComparison}
                className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                Annuler
              </button>
            )}
          </div>
        </div>

        <div className={`grid gap-8 ${comparePlayerStats ? 'md:grid-cols-2' : 'md:grid-cols-1 max-w-2xl mx-auto'}`}>
          <StatCard
            title={statLabels}
            stats={{
              sessions_count: playerStats.sessions_count,
              vitesse_max: playerStats.vitesse_max?.toFixed(2),
              vitesse_avg: playerStats.vitesse_avg?.toFixed(2),
              hsr_max: Math.round(playerStats.hsr_max),
              hsr_avg: Math.round(playerStats.hsr_avg),
              sprint_max: Math.round(playerStats.sprint_max),
              sprint_avg: Math.round(playerStats.sprint_avg),
              distance_max: playerStats.distance_max?.toFixed(2),
              distance_avg: playerStats.distance_avg?.toFixed(2),
              dec_max: Math.round(playerStats.dec_max),
              dec_avg: Math.round(playerStats.dec_avg),
              pp_max: Math.round(playerStats.pp_max),
              pp_avg: Math.round(playerStats.pp_avg),
            }}
            playerName={playerName}
          />

          {comparePlayerStats && (
            <StatCard
              title={statLabels}
              stats={{
                sessions_count: comparePlayerStats.sessions_count,
                vitesse_max: comparePlayerStats.vitesse_max?.toFixed(2),
                vitesse_avg: comparePlayerStats.vitesse_avg?.toFixed(2),
                hsr_max: Math.round(comparePlayerStats.hsr_max),
                hsr_avg: Math.round(comparePlayerStats.hsr_avg),
                sprint_max: Math.round(comparePlayerStats.sprint_max),
                sprint_avg: Math.round(comparePlayerStats.sprint_avg),
                distance_max: comparePlayerStats.distance_max?.toFixed(2),
                distance_avg: comparePlayerStats.distance_avg?.toFixed(2),
                dec_max: Math.round(comparePlayerStats.dec_max),
                dec_avg: Math.round(comparePlayerStats.dec_avg),
                pp_max: Math.round(comparePlayerStats.pp_max),
                pp_avg: Math.round(comparePlayerStats.pp_avg),
              }}
              playerName={compareWith}
            />
          )}
        </div>
      </div>
    </div>
  );
}
