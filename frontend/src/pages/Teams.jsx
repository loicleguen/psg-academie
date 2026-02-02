import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { organizationService } from '../services/organizationService';

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [academies, setAcademies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [formData, setFormData] = useState({ name: '', academy_id: '' });
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const academyFilter = searchParams.get('academy');

  const isAdminOrCoach = user?.role === 'admin' || user?.role === 'coach';

  useEffect(() => {
    loadData();
  }, [academyFilter]);

  const loadData = async () => {
    try {
      const [teamsData, academiesData] = await Promise.all([
        academyFilter
          ? organizationService.getTeamsByAcademy(academyFilter)
          : organizationService.getTeams(),
        organizationService.getAcademies()
      ]);
      setTeams(teamsData);
      setAcademies(academiesData);
    } catch (error) {
      console.error('Erreur lors du chargement des équipes:', error);
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setModalMode('create');
    setFormData({ name: '', academy_id: '' });
    setSelectedTeam(null);
    setShowModal(true);
  };

  const openEditModal = (team) => {
    setModalMode('edit');
    setFormData({ 
      name: team.name,
      academy_id: team.academy?.id || team.academy_id
    });
    setSelectedTeam(team);
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (modalMode === 'create') {
        await organizationService.createTeam(formData.name, parseInt(formData.academy_id));
      } else {
        await organizationService.updateTeam(selectedTeam.id, formData.name);
      }
      setShowModal(false);
      loadData();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Une erreur est survenue');
    }
  };

  const handleDelete = async (team) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette équipe ?')) return;
    
    try {
      await organizationService.deleteTeam(team.id);
      loadData();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  // Séparer équipes masculines et féminines
  const maleTeams = teams.filter(team => 
    team.name.includes(' H') || team.name.includes('Hommes')
  );
  const femaleTeams = teams.filter(team => 
    team.name.includes(' F') || team.name.includes('Femmes')
  );
  const otherTeams = teams.filter(team => 
    !team.name.includes(' H') && 
    !team.name.includes(' F') && 
    !team.name.includes('Hommes') && 
    !team.name.includes('Femmes')
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const TeamCard = ({ teams, title }) => (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-xl font-bold text-gray-700 mb-4">{title}</h2>
      <ul className="space-y-4">
        {teams.map((team) => (
          <li
            key={team.id}
            className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <div className="flex items-center flex-1">
              <span className="mr-4 text-blue-600 text-xl">•</span>
              <span className="text-2xl font-medium text-gray-900">
                {team.name}
              </span>
              {team.players && team.players.length > 0 && (
                <span className="ml-4 text-sm text-gray-500">
                  {team.players.length} joueur{team.players.length > 1 ? 's' : ''}
                </span>
              )}
            </div>
            
            {isAdminOrCoach && (
              <div className="flex space-x-2 ml-4">
                <button
                  onClick={() => openEditModal(team)}
                  className="text-blue-600 hover:text-blue-800 font-medium text-sm px-3 py-1"
                >
                  Modifier
                </button>
                <button
                  onClick={() => handleDelete(team)}
                  className="text-red-600 hover:text-red-800 font-medium text-sm px-3 py-1"
                >
                  Supprimer
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-4xl font-bold text-gray-900">TEAMS</h1>
            {isAdminOrCoach && (
              <button
                onClick={openCreateModal}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                + Ajouter une équipe
              </button>
            )}
          </div>

          {academyFilter && (
            <p className="text-center text-gray-600 mb-8">
              Filtré par : <span className="font-semibold">{academyFilter}</span>
              <button
                onClick={() => navigate('/teams')}
                className="ml-4 text-blue-600 hover:text-blue-800 text-sm"
              >
                Voir toutes
              </button>
            </p>
          )}

          {teams.length === 0 ? (
            <div className="text-center text-gray-500">
              <p className="text-xl">Aucune équipe enregistrée</p>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {maleTeams.length > 0 && <TeamCard teams={maleTeams} title="Hommes" />}
                {femaleTeams.length > 0 && <TeamCard teams={femaleTeams} title="Femmes" />}
              </div>
              
              {otherTeams.length > 0 && (
                <div className="mt-8">
                  <TeamCard teams={otherTeams} title="Autres" />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-4">
              {modalMode === 'create' ? 'Ajouter une équipe' : 'Modifier l\'équipe'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom de l'équipe
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="N1 H"
                />
              </div>
              {modalMode === 'create' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Académie
                  </label>
                  <select
                    required
                    value={formData.academy_id}
                    onChange={(e) => setFormData({ ...formData, academy_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Sélectionner une académie</option>
                    {academies.map(academy => (
                      <option key={academy.id} value={academy.id}>
                        {academy.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {modalMode === 'create' ? 'Créer' : 'Modifier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}