import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
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
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const compareWith = searchParams.get('compare');

  const [playerStats, setPlayerStats] = useState(null);
  const [comparePlayerStats, setComparePlayerStats] = useState(null);
  const [veoStats, setVeoStats] = useState(null);
  const [compareVeoStats, setCompareVeoStats] = useState(null);
  const [allPlayers, setAllPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [veoLoading, setVeoLoading] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState('');

  useEffect(() => {
    loadPlayerStats();
    loadAllPlayers();
  }, [playerName]);

  useEffect(() => {
    loadVeoStats();
  }, [playerName]);

  useEffect(() => {
    if (compareWith) {
      loadComparePlayerStats(compareWith);
    } else {
      setComparePlayerStats(null);
    }
  }, [compareWith]);

  useEffect(() => {
    if (compareWith) {
      loadCompareVeoStats(compareWith);
    } else {
      setCompareVeoStats(null);
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
      setCompareVeoStats(stats);
    } catch (error) {
      if (error?.response?.status !== 404) {
        console.error('Erreur chargement stats VEO comparaison:', error);
      }
      setCompareVeoStats(null);
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

  const handleCompare = () => {
    if (selectedPlayer && selectedPlayer !== playerName) {
      setSearchParams({ compare: selectedPlayer });
    }
  };

  const clearComparison = () => {
    setSelectedPlayer('');
    setSearchParams({});
    setCompareVeoStats(null);
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

  const StatRow = ({ label, value1, value2, color }) => (
    <div className="border-b pb-4">
      <p className="text-sm text-gray-600 font-medium mb-2">{label}</p>
      <div className={comparePlayerStats ? "grid grid-cols-2 gap-4" : "flex"}>
        <div>
          <p className="text-xs text-gray-500 mb-1">{playerStats.player_name}</p>
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

  const compareVeoMetricMap = (compareVeoStats?.metrics ?? []).reduce((acc, metric) => {
    acc[metric.slug] = metric.value;
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header avec bouton retour */}
        <button 
          onClick={() => navigate(-1)} 
          className="mb-6 text-blue-600 hover:text-blue-800 flex items-center transition-colors"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Retour
        </button>

        {/* Titre de la page */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Statistiques de {playerStats.player_name}
            {comparePlayerStats && ` vs ${comparePlayerStats.player_name}`}
          </h1>
          <p className="text-gray-600">Vue comparative des donnees joueur</p>
        </div>

        {/* Section de comparaison */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
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
                  .filter(name => name !== playerName)
                  .map(name => (
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

        {/* Statistiques en une seule colonne */}
        <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
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

          <StatRow 
            label="Vitesse Max (m/s)" 
            value1={playerStats.vitesse_max?.toFixed(2)} 
            value2={comparePlayerStats?.vitesse_max?.toFixed(2)}
            color="text-gray-900"
          />

          <StatRow 
            label="Vitesse Moyenne (m/s)" 
            value1={playerStats.vitesse_avg?.toFixed(2)} 
            value2={comparePlayerStats?.vitesse_avg?.toFixed(2)}
            color="text-gray-900"
          />

          <StatRow 
            label="HSR Max (m)" 
            value1={playerStats.hsr_max?.toFixed(0)} 
            value2={comparePlayerStats?.hsr_max?.toFixed(0)}
            color="text-orange-600"
          />

          <StatRow 
            label="HSR Moyen (m)" 
            value1={playerStats.hsr_avg?.toFixed(0)} 
            value2={comparePlayerStats?.hsr_avg?.toFixed(0)}
            color="text-orange-600"
          />

          <StatRow 
            label="Sprint Max (m)" 
            value1={playerStats.sprint_max?.toFixed(0)} 
            value2={comparePlayerStats?.sprint_max?.toFixed(0)}
            color="text-red-600"
          />

          <StatRow 
            label="Sprint Moyen (m)" 
            value1={playerStats.sprint_avg?.toFixed(0)} 
            value2={comparePlayerStats?.sprint_avg?.toFixed(0)}
            color="text-red-600"
          />

          <StatRow 
            label="Distance Max (m)" 
            value1={playerStats.distance_max?.toFixed(0)} 
            value2={comparePlayerStats?.distance_max?.toFixed(0)}
            color="text-green-600"
          />

          <StatRow 
            label="Distance Moyenne (m)" 
            value1={playerStats.distance_avg?.toFixed(0)} 
            value2={comparePlayerStats?.distance_avg?.toFixed(0)}
            color="text-green-600"
          />

          <StatRow 
            label="DEC Max" 
            value1={playerStats.dec_max?.toFixed(0)} 
            value2={comparePlayerStats?.dec_max?.toFixed(0)}
            color="text-purple-600"
          />

          <StatRow 
            label="DEC Moyen" 
            value1={playerStats.dec_avg?.toFixed(0)} 
            value2={comparePlayerStats?.dec_avg?.toFixed(0)}
            color="text-purple-600"
          />

          <StatRow 
            label="PP Max" 
            value1={playerStats.pp_max?.toFixed(2)} 
            value2={comparePlayerStats?.pp_max?.toFixed(2)}
            color="text-indigo-600"
          />

          <StatRow 
            label="PP Moyen" 
            value1={playerStats.pp_avg?.toFixed(2)} 
            value2={comparePlayerStats?.pp_avg?.toFixed(2)}
            color="text-indigo-600"
          />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 space-y-6 mt-8">
          <h2 className="text-2xl font-bold text-gray-900">Metriques VEO (moyenne par session)</h2>
          {veoLoading ? (
            <p className="text-gray-500 text-sm">Chargement des metriques VEO...</p>
          ) : !veoStats ? (
            <p className="text-gray-500 text-sm">
              Aucune metrique VEO disponible pour ce joueur sur les sessions disponibles.
            </p>
          ) : (
            <>
              <div className="border-b pb-3">
                <p className="text-sm text-gray-600 font-medium mb-2">Nombre de sessions</p>
                <div className={comparePlayerStats ? "grid grid-cols-2 gap-4" : "flex"}>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">
                      {veoStats.player_name || playerStats.player_name}
                    </p>
                    <p className="text-2xl font-bold text-blue-600">
                      {veoStats.sessions_count}
                    </p>
                  </div>
                  {comparePlayerStats && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">
                        {compareVeoStats?.player_name || comparePlayerStats.player_name}
                      </p>
                      <p className="text-2xl font-bold text-blue-600">
                        {compareVeoStats?.sessions_count ?? 0}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {VEO_PLAYER_METRIC_ORDER.map((slug) => (
                <StatRow
                  key={slug}
                  label={VEO_PLAYER_METRIC_LABELS[slug] || slug}
                  value1={formatVeoMetricValue(veoMetricMap[slug])}
                  value2={formatVeoMetricValue(compareVeoMetricMap[slug])}
                  color="text-gray-900"
                />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
