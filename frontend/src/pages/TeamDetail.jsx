import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { organizationService } from '../services/organizationService';

export default function TeamDetail() {
  const { teamName } = useParams();
  const navigate = useNavigate();
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlayers();
  }, [teamName]);

  const loadPlayers = async () => {
    try {
      const data = await organizationService.getTeamPlayers(teamName);
      const playersData = (data || []).filter(p => p.is_active === true);
    setPlayers(playersData.sort((a, b) => (a.player_name || a.full_name).localeCompare(b.player_name || b.full_name)));
    } catch (error) {
      console.error('Erreur lors du chargement des joueurs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <button
            onClick={() => navigate('/teams')}
            className="mb-6 text-blue-600 hover:text-blue-800 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Retour aux équipes
          </button>

          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {decodeURIComponent(teamName)}
          </h1>

          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                Joueurs ({players.length})
              </h2>
            </div>

            {players.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p className="text-xl">Aucun joueur dans cette équipe</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        #
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Nom du joueur
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Poste
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {players.map((player, index) => (
                      <tr key={player.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {index + 1}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => navigate(`/players/${encodeURIComponent(player.player_name || player.full_name)}`)}
                            className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            {player.player_name || player.full_name || 'N/A'}
                          </button>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{player.email}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{player.position || 'N/A'}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
