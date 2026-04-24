import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { organizationService } from '../services/organizationService';

export default function TeamDetail() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const [players, setPlayers] = useState([]);
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
  loadPlayers();
  // eslint-disable-next-line
}, [teamId]);

  useEffect(() => {
    console.log('team:', team);
  }, [team]);

  const loadPlayers = async () => {
    try {
      const [playersData, teamData] = await Promise.all([
        organizationService.getTeamPlayersById(teamId),
        organizationService.getTeamById(teamId)
      ]);
      const playersFiltered = (playersData || []).filter(p => p.is_active === true);
      setPlayers(
        playersFiltered.sort((a, b) =>
          (a.player_name || a.full_name).localeCompare(b.player_name || b.full_name)
        )
      );
      setTeam(teamData);
    } catch (error) {
      console.error('Erreur lors du chargement des joueurs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white/60 min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white/10 min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="bg-white/60 text-4xl font-bold text-center text-black mb-4">
            {team && team.academy && team.academy.country
              ? `${team.academy.country.name} / ${team.academy.name} / ${team.name}`
              : team && team.academy
                ? `${team.academy.name} / ${team.name}`
                : team
                  ? team.name
                  : ''}
          </h1>

          <div className="bg-white/60 rounded-lg shadow-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
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
                      <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                        #
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                        Nom du joueur
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                        Poste
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white/10 divide-y divide-gray-400">
                    {players.map((player, index) => (
                      <tr key={player.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-black">
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
                          <div className="text-sm text-black">{player.position || 'N/A'}</div>
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
