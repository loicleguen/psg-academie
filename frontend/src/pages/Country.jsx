import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { organizationService } from '../services/organizationService';

export default function Country() {
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' or 'edit'
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [formData, setFormData] = useState({ name: '' });
  const navigate = useNavigate();
  const { user } = useAuth();

  const isAdminOrCoach = user?.role === 'admin' || user?.role === 'coach';

  useEffect(() => {
    loadCountries();
  }, []);

  const loadCountries = async () => {
    try {
      const data = await organizationService.getCountries();
      setCountries(data);
    } catch (error) {
      console.error('Erreur lors du chargement des pays:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCountryClick = (countryName) => {
    navigate(`/academies?country=${encodeURIComponent(countryName)}`);
  };

  const openCreateModal = () => {
    setModalMode('create');
    setFormData({ name: '' });
    setSelectedCountry(null);
    setShowModal(true);
  };

  const openEditModal = (country) => {
    setModalMode('edit');
    setFormData({ name: country.name });
    setSelectedCountry(country);
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (modalMode === 'create') {
        await organizationService.createCountry(formData.name);
      } else {
        await organizationService.updateCountry(selectedCountry.name, formData.name);
      }
      setShowModal(false);
      loadCountries();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Une erreur est survenue');
    }
  };

  const handleDelete = async (countryId) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce pays ?')) return;
    
    try {
      await organizationService.deleteCountry(country.name);
      loadCountries();
    } catch (error) {
      console.error('Erreur:', error);
      alert(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const countryFlags = {
    'France': '🇫🇷',
    'Sénégal': '🇸🇳',
    'Allemagne': '🇩🇪',
    'Belgique': '🇧🇪',
    'Portugal': '🇵🇹',
    'Suisse': '🇨🇭',
    'Espagne': '🇪🇸',
    'Italie': '🇮🇹',
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
          <div className="flex justify-between items-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900">COUNTRY</h1>
            {isAdminOrCoach && (
              <button
                onClick={openCreateModal}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                + Ajouter un pays
              </button>
            )}
          </div>

          {countries.length === 0 ? (
            <div className="text-center text-gray-500">
              <p className="text-xl">Aucun pays enregistré</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {countries.map((country) => (
                <div
                  key={country.id}
                  className="bg-white rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 overflow-hidden"
                >
                  <div 
                    onClick={() => handleCountryClick(country.name)}
                    className="p-8 flex flex-col items-center cursor-pointer transform hover:scale-105 transition-transform"
                  >
                    <div className="text-8xl mb-4">
                      {countryFlags[country.name] || '🏳️'}
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 text-center">
                      {country.name}
                    </h2>
                    {country.academies && country.academies.length > 0 && (
                      <p className="text-sm text-gray-500 mt-2">
                        {country.academies.length} académie{country.academies.length > 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                  
                  {isAdminOrCoach && (
                    <div className="border-t border-gray-200 bg-gray-50 px-4 py-3 flex justify-end space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditModal(country);
                        }}
                        className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                      >
                        Modifier
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(country);
                        }}
                        className="text-red-600 hover:text-red-800 font-medium text-sm"
                      >
                        Supprimer
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold mb-4">
              {modalMode === 'create' ? 'Ajouter un pays' : 'Modifier le pays'}
            </h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom du pays
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="France"
                />
              </div>
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