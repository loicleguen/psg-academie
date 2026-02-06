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
  const [sessionInfo, setSessionInfo] = useState(null);
  const [loadingSessionInfo, setLoadingSessionInfo] = useState(true);

  const sessionTitle = decodeURIComponent(sessionId);

  // Récupérer les infos de la session pour le rapport hebdo
  useEffect(() => {
    const fetchSessionInfo = async () => {
      setLoadingSessionInfo(true);
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
      } finally {
        setLoadingSessionInfo(false);
      }
    };
    fetchSessionInfo();
  }, [sessionTitle]);

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
      
      const url = `/catapult/reports/weekly.png?team_id=${sessionInfo.team_id}&week=${weekNumber}&year=${year}`;
      setWeeklyReportUrl(url);
      setShowWeeklyReport(true);
    } catch (err) {
      setError('Erreur lors de la génération du rapport hebdomadaire');
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
      description: 'Analyse individuelle de chaque joueur sur la semaine',
      icon: UserGroupIcon,
      available: false,
      onClick: null
    }
  ];

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        {/* Header with back button */}
        <div className="mb-6">
          <Link
            to="/catapult/sessions"
            className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-700"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Retour aux sessions
          </Link>
          <h1 className="mt-4 text-3xl font-bold text-gray-900">
            {sessionTitle}
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Choisissez un type de rapport à générer
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-6">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Report type cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
          {reportTypes.map((report) => {
            const Icon = report.icon;
            return (
              <button
                key={report.id}
                onClick={report.onClick}
                disabled={!report.available || loading}
                className={`
                  relative rounded-lg border p-6 text-left transition-all
                  ${report.available 
                    ? 'border-gray-300 bg-white hover:border-blue-500 hover:shadow-lg cursor-pointer' 
                    : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
                  ${loading && report.available ? 'opacity-50' : ''}
                `}
              >
                <div className="flex items-center justify-between mb-4">
                  <Icon className={`h-8 w-8 ${report.available ? 'text-blue-600' : 'text-gray-400'}`} />
                  {!report.available && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                      Bientôt disponible
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {report.title}
                </h3>
                <p className="text-sm text-gray-500">
                  {report.description}
                </p>
                {loading && report.available && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-lg">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </button>
            );
          })}
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
                href={`${api.defaults.baseURL}${weeklyReportUrl}`}
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
                src={`${api.defaults.baseURL}${weeklyReportUrl}`}
                alt="Rapport hebdomadaire"
                className="max-w-full h-auto rounded-lg"
                onError={() => setError('Erreur lors du chargement du rapport. Aucune séance trouvée pour cette semaine.')}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
