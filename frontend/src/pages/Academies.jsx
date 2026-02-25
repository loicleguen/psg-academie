import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { organizationService } from '../services/organizationService';

export default function Academies() {
  const [academies, setAcademies] = useState([]);
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [selectedAcademy, setSelectedAcademy] = useState(null);
  const [formData, setFormData] = useState({ name: '', country_id: '' });
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const countryFilter = searchParams.get('country');

  const isAdminOrCoach = user?.role === 'admin' || user?.role === 'coach';

  useEffect(() => {
    loadData();
  }, [countryFilter]);

  const loadData = async () => {
    try {
      const [academiesData, countriesData] = await Promise.all([
        countryFilter 
          ? organizationService.getAcademiesByCountry(countryFilter)
          : organizationService.getAcademies(),
        organizationService.getCountries()
      ]);
      setAcademies(academiesData);
      setCountries(countriesData);
    } catch (error) {
      console.error('Erreur:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcademyClick = (academyName) => {
    navigate(`/teams?academy=${encodeURIComponent(academyName)}`);
  };

  const openCreateModal = () => {
    setModalMode('create');
    setFormData({ name: '', country_id: '' });
    setSelectedAcademy(null);
    setShowModal(true);
  };

  const openEditModal = (academy) => {
    setModalMode('edit');
    setFormData({ 
      name: academy.name, 
      country_id: academy.country?.id || academy.country_id 
    });
    setSelectedAcademy(academy);
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (modalMode === 'create') {
        await organizationService.createAcademy(formData.name, parseInt(formData.country_id));
      } else {
        await organizationService.updateAcademy(selectedAcademy.name, formData.name);
      }
      setShowModal(false);
      loadData();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Une erreur est survenue');
    }
  };

  const handleDelete = async (academy) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette académie ?')) return;
    
    try {
      await organizationService.deleteAcademy(academy.name);
      loadData();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-3 items-center gap-4 mb-12">
            <h1 className="justify-self-start inline-block bg-white/50 px-4 py-2 rounded-md text-4xl font-bold text-black">
              ACADEMY
            </h1>
            <div className="col-start-2 flex justify-center">
              {isAdminOrCoach && (
                <button
                  onClick={openCreateModal}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  + Ajouter une académie
                </button>
              )}
            </div>
            <div className="col-start-3" />
          </div>
          
          {countryFilter && (
            <p className="bg-white/50 max-w-md mx-auto px-6 text-center text-black mb-12 rounded-lg">
              Filtré par : <span className="font-semibold">{countryFilter}</span>
              <button
                onClick={() => navigate('/academies')}
                className="ml-4 text-blue-600 hover:text-blue-800 text-m"
              >
                Voir toutes
              </button>
            </p>
          )}

          <div className="max-w-xl mx-auto">
            <div className="bg-white/70 rounded-lg shadow-lg p-8">
              {academies.length === 0 ? (
                <div className="text-center text-gray-500 py-6">
                  <p className="text-lg">Aucune académie enregistrée</p>
                </div>
              ) : (
                <ul className="space-y-0">
                  {academies.map((academy) => (
                    <li
                      key={academy.id}
                      className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      <div
                        onClick={() => handleAcademyClick(academy.name)}
                        className="flex items-center flex-1 cursor-pointer"
                      >
                        <span className="mr-4 text-blue-600 text-xl">•</span>
                        <span className="text-2xl font-medium text-gray-900 hover:text-blue-600">
                          {academy.name}
                        </span>
                        {academy.teams && academy.teams.length > 0 && (
                          <span className="ml-4 text-sm text-gray-500">
                            {academy.teams.length} équipe{academy.teams.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>

                      {isAdminOrCoach && (
                        <div className="flex space-x-2 ml-4">
                          <button
                            onClick={(e) => { e.stopPropagation(); openEditModal(academy); }}
                            className="text-blue-600 hover:text-blue-800 font-medium text-sm px-3 py-1"
                          >
                            Modifier
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(academy); }}
                            className="text-red-600 hover:text-red-800 font-medium text-sm px-3 py-1"
                          >
                            Supprimer
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white/60 rounded-lg p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-4">
              {modalMode === 'create' ? 'Ajouter une académie' : 'Modifier l\'académie'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom de l'académie
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Paris"
                />
              </div>
              {modalMode === 'create' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Pays
                  </label>
                  <select
                    required
                    value={formData.country_id}
                    onChange={(e) => setFormData({ ...formData, country_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Sélectionner un pays</option>
                    {countries.map(country => (
                      <option key={country.id} value={country.id}>
                        {country.name}
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