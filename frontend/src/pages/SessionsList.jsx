import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
import { useAuth } from '../context/AuthContext';

export default function SessionsList() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();

  const isAdminOrCoach = user?.role === 'admin' || user?.role === 'coach';

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await catapultService.getSessions();
      setSessions(data);
    } catch (err) {
      setError('Erreur lors du chargement des sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionTitle, e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm(`Êtes-vous sûr de vouloir supprimer la session "${sessionTitle}" ?`)) {
      return;
    }

    try {
      await catapultService.deleteSession(sessionTitle);
      await loadSessions();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erreur lors de la suppression');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="bg-white/60 max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="grid grid-cols-3 items-center gap-4 mb-12">
          <h1 className="justify-self-start inline-block bg-white/50 px-4 py-2 rounded-md text-4xl font-bold text-black">
            SESSIONS ({sessions.length})
          </h1>
          <div className="col-start-2 flex justify-center">
            {isAdminOrCoach && (
              <Link
                to="/catapult/upload"
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors inline-flex items-center"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Nouvelle session
              </Link>
            )}
          </div>
          <div className="col-start-3" />
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-6">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {sessions.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">Aucune session</h3>
            <p className="mt-1 text-sm text-gray-500">
              Commencez par uploader un fichier CSV Catapult
            </p>
            <div className="mt-6">
              <Link
                to="/catapult/upload"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Uploader un fichier
              </Link>
            </div>
          </div>
        ) : (
          <div className="bg-white/80 shadow overflow-hidden sm:rounded-md max-w-2xl mx-auto">
            <ul className="divide-y divide-gray-800">
              {sessions.map((session, index) => (
                <li key={index} className="relative">
                  <Link
                    to={`/catapult/sessions/${encodeURIComponent(session.session_title)}`}
                    className="block hover:bg-gray-50 transition duration-150"
                  >
                    <div className="px-4 py-2 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0 pr-4">
                          <p className="text-lg font-bold text-green-600 truncate">
                            {session.session_title}
                          </p>
                          <div className="mt-1 flex items-center text-sm text-black">
                            <svg
                              className="shrink-0 mr-1.5 h-5 w-5 text-gray-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                              />
                            </svg>
                            {new Date(session.session_date).toLocaleDateString('fr-FR', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                            })}
                          </div>
                          <div className="mt-1 flex items-center text-sm text-black">
                            <svg
                              className="shrink-0 mr-1.5 h-5 w-5 text-gray-400"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                              />
                            </svg>
                            {session.player_count || 0} joueurs
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {isAdminOrCoach && (
                            <button
                              onClick={(e) => handleDeleteSession(session.session_title, e)}
                              className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
                              title="Supprimer la session"
                            >
                              <svg
                                className="h-5 w-5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                            </button>
                          )}
                          <svg
                            className="h-5 w-5 text-gray-400"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
