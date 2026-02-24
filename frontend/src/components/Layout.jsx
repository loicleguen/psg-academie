import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-transparent">
      <nav className="bg-white/50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/country" className="inline-flex items-center px-4 h-10 bg-blue-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-xl font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-5 focus:ring-offset-5 focus:ring-black">PSG Académie</Link>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8 sm:items-center">
                <Link
                  to="/veo"
                  className="inline-flex items-center px-4 h-10 bg-blue-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-5 focus:ring-offset-5 focus:ring-black"
                >
                  VEO
                </Link>
                <Link
                  to="/catapult/sessions"
                  className="inline-flex items-center px-4 h-10 bg-blue-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-5 focus:ring-offset-5 focus:ring-black"
                >
                  Sessions Catapult
                </Link>
                <Link
                      to="/admin"
                      className="bg-blue-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-5 focus:ring-offset-5 focus:ring-black"
                    >
                      Coach Pannel
                    </Link>
              </div>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:items-center">
              <div className="ml-3 relative">
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-700">{user?.email}</span>
                  <button
                    onClick={handleLogout}
                    className="bg-red-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-red-700"
                  >
                    Déconnexion
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main>{children}</main>
    </div>
  );
}
