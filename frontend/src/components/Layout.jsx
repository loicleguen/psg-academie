import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Détection des onglets actifs
  const isPSGAcadémieActive =
    location.pathname.startsWith('/country') ||
    location.pathname.startsWith('/academies') ||
    location.pathname.startsWith('/teams') ||
    /^\/teams\/\d+/.test(location.pathname);

  const isVEOActive = location.pathname.startsWith('/veo');

  const isCalendarActive = location.pathname.startsWith('/calendar');

  const isSessionCatapultActive =
    location.pathname.startsWith('/catapult/sessions') ||
    location.pathname.startsWith('/catapult/upload') ||
    /^\/catapult\/sessions\/[^/]+$/.test(location.pathname);

  const isCoachPannelActive =
    location.pathname.startsWith('/admin') ||
    location.pathname.startsWith('/players/');

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
              <div className="shrink-0 flex items-center">
                <NavLink
                  to="/country"
                  className={
                    "inline-flex items-center px-4 h-10 bg-blue-500 py-2 border border-transparent rounded-md shadow-sm text-xl font-medium text-white hover:bg-blue-700 " +
                    (isPSGAcadémieActive ? "ring-5 ring-offset-5 ring-black" : "")
                  }
                >
                  PSG Académie
                </NavLink>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8 sm:items-center">
                <NavLink
                  to="/veo"
                  className={
                    "inline-flex items-center px-4 h-10 bg-blue-500 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 " +
                    (isVEOActive ? "ring-5 ring-offset-5 ring-black" : "")
                  }
                  >
                  VEO
                </NavLink>
                <NavLink
                  to="/calendar"
                  className={
                    "inline-flex items-center px-4 h-10 bg-blue-500 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 " +
                    (isCalendarActive ? "ring-5 ring-offset-5 ring-black" : "")
                  }
                >
                  Calendrier
                </NavLink>
                <NavLink
                  to="/catapult/sessions"
                  className={
                    "inline-flex items-center px-4 h-10 bg-blue-500 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 " +
                    (isSessionCatapultActive ? "ring-5 ring-offset-5 ring-black" : "")
                  }
                >
                  Sessions Catapult
                </NavLink>
                <NavLink
                  to="/admin"
                  className={
                    "bg-blue-500 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 " +
                    (isCoachPannelActive ? "ring-5 ring-offset-5 ring-black" : "")
                  }
                >
                  Coach Pannel
                </NavLink>
              </div>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:items-center">
              <div className="ml-3 relative">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => {
                      const profileSlug = user?.player_name || user?.full_name;
                      if (!profileSlug) return;
                      navigate(`/players/${encodeURIComponent(profileSlug)}?tab=info`);
                    }}
                    className="text-sm text-gray-700 hover:text-blue-500 hover:underline cursor-pointer transition"
                  >
                    {user?.full_name}
                  </button>
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
