import { useState, useEffect } from 'react';
import api from '../services/api';

export default function WeeklyReport() {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [weekNumber, setWeekNumber] = useState(3); // Current week
  const [year, setYear] = useState(2026);
  const [reportUrl, setReportUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTeams();
    // Calculate current week number
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 1);
    const diff = now - start;
    const oneWeek = 1000 * 60 * 60 * 24 * 7;
    const week = Math.ceil(diff / oneWeek);
    setWeekNumber(week);
    setYear(now.getFullYear());
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await api.get('/catapult/teams');
      setTeams(response.data);
    } catch (err) {
      console.error('Erreur chargement équipes:', err);
    }
  };

  const generateReport = async () => {
    if (!selectedTeam) {
      alert('Veuillez sélectionner une équipe');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `/catapult/reports/weekly.png?team_id=${selectedTeam}&week=${weekNumber}&year=${year}`;
      setReportUrl(url);
    } catch (err) {
      setError('Erreur lors de la génération du rapport');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Rapport Hebdomadaire</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Équipe
            </label>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Sélectionner une équipe</option>
              {teams.map(team => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Numéro de semaine
            </label>
            <input
              type="number"
              min="1"
              max="53"
              value={weekNumber}
              onChange={(e) => setWeekNumber(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Année
            </label>
            <input
              type="number"
              min="2020"
              max="2030"
              value={year}
              onChange={(e) => setYear(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={loading || !selectedTeam}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Génération...' : 'Générer le rapport'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>

      {reportUrl && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">
              Rapport Semaine {weekNumber} - {year}
            </h2>
            <a
              href={`${api.defaults.baseURL}${reportUrl}`}
              download={`rapport_semaine_${weekNumber}_${year}.png`}
              className="bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700"
            >
              Télécharger
            </a>
          </div>
          <div className="overflow-auto">
            <img
              src={`${api.defaults.baseURL}${reportUrl}`}
              alt={`Rapport semaine ${weekNumber}`}
              className="w-full h-auto"
              onError={() => setError('Erreur lors du chargement du rapport. Aucune séance trouvée pour cette semaine.')}
            />
          </div>
        </div>
      )}
    </div>
  );
}
