import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import CatapultUpload from './pages/CatapultUpload';
import SessionsList from './pages/SessionsList';
import SessionDetail from './pages/SessionDetail';
import Country from './pages/Country';
import Academies from './pages/Academies';
import Teams from './pages/Teams';
import TeamDetail from './pages/TeamDetail';
import PlayerDetail from './pages/PlayerDetail';
import Veo from './pages/Veo';
import AdminPannel from './pages/AdminPannel';
import WeeklyReport from './pages/WeeklyReport';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          <Route
            path="/"
            element={<Navigate to="/country" replace />}
          />
          
          <Route
            path="/country"
            element={
              <ProtectedRoute>
                <Layout>
                  <Country />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/academies"
            element={
              <ProtectedRoute>
                <Layout>
                  <Academies />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/teams"
            element={
              <ProtectedRoute>
                <Layout>
                  <Teams />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/teams/:teamName"
            element={
              <ProtectedRoute>
                <Layout>
                  <TeamDetail />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/players/:playerName"
            element={
              <ProtectedRoute>
                <Layout>
                  <PlayerDetail />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/veo"
            element={
              <ProtectedRoute>
                <Layout>
                  <Veo />
                </Layout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/catapult/upload"
            element={
              <ProtectedRoute>
                <Layout>
                  <CatapultUpload />
                </Layout>
              </ProtectedRoute>
            }
          />
          
          <Route
            path="/catapult/sessions"
            element={
              <ProtectedRoute>
                <Layout>
                  <SessionsList />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/catapult/sessions/:sessionId"
            element={
              <ProtectedRoute>
                <Layout>
                  <SessionDetail />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredRole="admin">
                <Layout>
                  <AdminPannel />
                </Layout>
              </ProtectedRoute>
            }
          />

          <Route
            path="/catapult/weekly-report"
            element={
              <ProtectedRoute>
                <Layout>
                  <WeeklyReport />
                </Layout>
              </ProtectedRoute>
            }
          />
          
          <Route path="*" element={<Navigate to="/country" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
