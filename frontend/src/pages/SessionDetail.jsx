// SessionDetail.jsx
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
import api from '../services/api';
import { ChartBarIcon, DocumentChartBarIcon, UserGroupIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

export default function SessionDetail() {
  const { sessionId } = useParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reportImage, setReportImage] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [weeklyReportUrl, setWeeklyReportUrl] = useState(null);
  const [showWeeklyReport, setShowWeeklyReport] = useState(false);
  const [individualReportUrl, setIndividualReportUrl] = useState(null);
  const [showIndividualReport, setShowIndividualReport] = useState(false);
  const [availablePlayers, setAvailablePlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [sessionInfo, setSessionInfo] = useState(null);

  const sessionTitle = decodeURIComponent(sessionId);

  // Récupérer les infos de la session pour le rapport hebdo
  useEffect(() => {
    const fetchSessionInfo = async () => {
      try {
        const response = await api.get('/catapult/sessions');
        console.log('All sessions:', response.data);
        console.log('Looking for session:', sessionTitle);
        const session = response.data.find(s => s.session_title === sessionTitle);
        console.log('Found session:', session);
        if (session) {
          setSessionInfo(session);
          console.log('Session info set:', session);
        } else {
          console.warn('Session not found in list');
        }
      } catch (err) {
        console.error('Erreur récupération session:', err);
      }
    };
    fetchSessionInfo();
  }, [sessionTitle]);

  // Récupérer la liste des joueurs de la semaine pour le rapport individuel
  useEffect(() => {
    const fetchWeekPlayers = async () => {
      if (!sessionInfo || !sessionInfo.week || !sessionInfo.year) {
        return;
      }
      
      try {
        const response = await api.get('/catapult/players-by-week', {
          params: {
            week: sessionInfo.week,
            year: sessionInfo.year
          }
        });
        console.log('Players for week:', response.data);
        setAvailablePlayers(response.data);
        
        // Présélectionner le premier joueur si disponible
        if (response.data.length > 0) {
          setSelectedPlayer(response.data[0]);
        }
      } catch (err) {
        console.error('Erreur récupération joueurs semaine:', err);
      }
    };
    
    fetchWeekPlayers();
  }, [sessionInfo]);


  const handleGenerateSessionReport = async () => {
    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowWeeklyReport(false);
      
      const data = await catapultService.generateSessionReport(sessionTitle);
      
      if (data.report_image) {
        setReportImage(`data:image/png;base64,${data.report_image}`);
        setShowReport(true);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération du rapport');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateWeeklyReport = async () => {
    console.log('sessionInfo:', sessionInfo);
    if (!sessionInfo) {
      setError('Informations de la session manquantes (sessionInfo null)');
      return;
    }
    if (!sessionInfo.team_id) {
      setError('Informations de la session manquantes (team_id manquant)');
      console.error('sessionInfo without team_id:', sessionInfo);
      return;
    }
    if (!sessionInfo.date) {
      setError('Informations de la session manquantes (date manquante)');
      console.error('sessionInfo without date:', sessionInfo);
      return;
    }

    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowWeeklyReport(false);
      
      // Utiliser directement le numéro de semaine ISO calculé par le backend
      const weekNumber = sessionInfo.week;
      const year = sessionInfo.year;
      
      console.log('Session date:', sessionInfo.date);
      console.log('Year (from backend):', year);
      console.log('Week number (from backend):', weekNumber);
      
      if (!weekNumber || !year) {
        setError('Numéro de semaine manquant');
        setLoading(false);
        return;
      }
      
      // Fetch avec token d'authentification
      const response = await api.get('/catapult/reports/weekly.png', {
        params: {
          team_id: sessionInfo.team_id,
          week: weekNumber,
          year: year
        },
        responseType: 'blob'
      });
      
      // Créer un object URL à partir du blob
      const imageUrl = URL.createObjectURL(response.data);
      setWeeklyReportUrl(imageUrl);
      setShowWeeklyReport(true);
    } catch (err) {
      setError('Erreur lors de la génération du rapport hebdomadaire');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };


  const handleGenerateIndividualReport = async () => {
    if (!sessionInfo) {
      setError('Informations de la session manquantes');
      return;
    }
    if (!selectedPlayer) {
      setError('Veuillez sélectionner un joueur');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowWeeklyReport(false);
      setShowIndividualReport(false);
      
      const weekNumber = sessionInfo.week;
      const year = sessionInfo.year;
      
      if (!weekNumber || !year) {
        setError('Numéro de semaine manquant');
        setLoading(false);
        return;
      }
      
      // Fetch avec token d'authentification
      const response = await api.get('/catapult/reports/individual-week.png', {
        params: {
          player_name: selectedPlayer,
          week: weekNumber,
          year: year
        },
        responseType: 'blob'
      });
      
      // Créer un object URL à partir du blob
      const imageUrl = URL.createObjectURL(response.data);
      setIndividualReportUrl(imageUrl);
      setShowIndividualReport(true);
    } catch (err) {
      setError('Erreur lors de la génération du rapport individuel');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const reportTypes = [
    {
      id: 'session',
      title: 'Rapport de séance',
      description: 'Analyse complète de la session avec graphiques et statistiques des joueurs',
      icon: ChartBarIcon,
      available: true,
      onClick: handleGenerateSessionReport
    },
    {
      id: 'weekly',
      title: 'Rapport Hebdomadaire',
      description: 'Synthèse de la semaine d\'entraînement avec comparaison des sessions',
      icon: DocumentChartBarIcon,
      available: true,
      onClick: handleGenerateWeeklyReport
    },
    {
      id: 'individual',
      title: 'Rapport semaine individuel',
      description: 'Analyse individuelle du joueur sur la semaine',
      icon: UserGroupIcon,
      available: true,
      onClick: handleGenerateIndividualReport
    }
  ];

  return (
    <div className="max-w-5xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        {/* Header with back button */}
        <div className="mb-6">
          <Link
            to="/catapult/sessions"
            className="inline-flex text-xl font-medium text-orange-600 hover:text-black"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Retour aux sessions
          </Link>
          <h1 className="inline-block-center bg-white/50 px-4 py-2 rounded-md text-3xl text-center font-bold text-gray-900">
            {sessionTitle}
          </h1>
          <p className="justify-self-center inline-block-center bg-white/50 rounded-md mt-2 text-m text-center text-black">
            Choisissez un type de rapport à générer
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-6">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Report type cards with player selection above individual report */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
          {/* Première carte: Rapport de séance */}
          <button
            onClick={reportTypes[0].onClick}
            disabled={!reportTypes[0].available || loading}
            className={`
              relative rounded-lg border p-6 text-left transition-all
              ${reportTypes[0].available 
                ? 'border-gray-300 bg-white/70 hover:border-blue-500 hover:shadow-lg cursor-pointer' 
                : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
              ${loading && reportTypes[0].available ? 'opacity-50' : ''}
            `}
          >
            <div className="flex items-center justify-between mb-4">
              <ChartBarIcon className={`h-8 w-8 ${reportTypes[0].available ? 'text-blue-600' : 'text-gray-400'}`} />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {reportTypes[0].title}
            </h3>
            <p className="text-sm text-gray-900">
              {reportTypes[0].description}
            </p>
            {loading && reportTypes[0].available && (
              <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-lg">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}
          </button>

          {/* Deuxième carte: Rapport Hebdomadaire */}
          <button
            onClick={reportTypes[1].onClick}
            disabled={!reportTypes[1].available || loading}
            className={`
              relative rounded-lg border p-6 text-left transition-all
              ${reportTypes[1].available 
                ? 'border-gray-300 bg-white/70 hover:border-blue-500 hover:shadow-lg cursor-pointer' 
                : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
              ${loading && reportTypes[1].available ? 'opacity-50' : ''}
            `}
          >
            <div className="flex items-center justify-between mb-4">
              <DocumentChartBarIcon className={`h-8 w-8 ${reportTypes[1].available ? 'text-blue-600' : 'text-gray-400'}`} />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {reportTypes[1].title}
            </h3>
            <p className="text-sm text-gray-900">
              {reportTypes[1].description}
            </p>
            {loading && reportTypes[1].available && (
              <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-lg">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}
          </button>

          {/* Troisième colonne: Player selection + Rapport individuel */}
          <div className="space-y-6">
            {/* Player selection for individual report */}
            {availablePlayers.length > 0 && (
              <div className="bg-white/70 rounded-lg shadow p-6">
                <label htmlFor="player-select" className="block text-sm font-medium text-gray-700 mb-2">
                  Sélectionner un joueur pour le rapport individuel
                </label>
                <select
                  id="player-select"
                  value={selectedPlayer}
                  onChange={(e) => setSelectedPlayer(e.target.value)}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                >
                  {availablePlayers.map((player) => (
                    <option key={player} value={player}>
                      {player}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Troisième carte: Rapport semaine individuel */}
            <button
              onClick={reportTypes[2].onClick}
              disabled={!reportTypes[2].available || loading}
              className={`
                relative rounded-lg border p-6 text-left transition-all w-full
                ${reportTypes[2].available 
                  ? 'border-gray-300 bg-white/70 hover:border-blue-500 hover:shadow-lg cursor-pointer' 
                  : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
                ${loading && reportTypes[2].available ? 'opacity-50' : ''}
              `}
            >
              <div className="flex items-center justify-between mb-4">
                <UserGroupIcon className={`h-8 w-8 ${reportTypes[2].available ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {reportTypes[2].title}
              </h3>
              <p className="text-sm text-gray-900">
                {reportTypes[2].description}
              </p>
              {loading && reportTypes[2].available && (
                <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-lg">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              )}
            </button>
          </div>
        </div>

        {/* Display session report image */}
        {showReport && reportImage && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport de séance</h2>
              <a
                href={reportImage}
                download={`rapport-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={reportImage}
                alt="Rapport de séance"
                className="max-w-full h-auto rounded-lg"
              />
            </div>
          </div>
        )}

        {/* Display weekly report image */}
        {showWeeklyReport && weeklyReportUrl && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport Hebdomadaire</h2>
              <a
                href={weeklyReportUrl}
                download={`rapport-hebdo-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={weeklyReportUrl}
                alt="Rapport hebdomadaire"
                className="max-w-full h-auto rounded-lg"
                onError={() => setError('Erreur lors du chargement du rapport. Aucune séance trouvée pour cette semaine.')}
              />
            </div>
          </div>
        )}
        {/* Display individual report image */}
        {showIndividualReport && individualReportUrl && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport Semaine Individuel</h2>
              <a
                href={individualReportUrl}
                download={`rapport-individuel-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={individualReportUrl}
                alt="Rapport semaine individuel"
                className="max-w-full h-auto rounded-lg"
                onError={() => setError('Erreur lors du chargement du rapport individuel.')}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
