import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AdminPannel() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [filter, setFilter] = useState('all'); // all, admin, coach, player, team
  const [selectedTeamId, setSelectedTeamId] = useState('');
  const [editingUser, setEditingUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchUsers();
    fetchTeams();
  }, []);

  useEffect(() => {
    filterUsers();
  }, [users, filter, selectedTeamId]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/auth/users');
      setUsers(response.data);
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des utilisateurs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTeams = async () => {
    try {
      const response = await api.get('/teams/');
      const data = response.data;
      if (Array.isArray(data)) {
        setTeams(data);
      } else if (data && Array.isArray(data.teams)) {
        setTeams(data.teams);
      } else if (data && Array.isArray(data.data)) {
        setTeams(data.data);
      } else {
        setTeams([]);
        console.warn('Unexpected /teams response shape:', data);
      }
    } catch (err) {
      console.error('Erreur chargement teams:', err, err?.response?.status, err?.response?.data);
      setTeams([]);
    }
  };

  const filterUsers = () => {
    const sortActiveThenAlpha = (a, b) => {
      // Les actifs en premier
      if (a.is_active === b.is_active) {
        // si même statut, trier alphabétiquement sur le nom complet
        return (a.full_name || '').localeCompare(b.full_name || '');
      }
      return a.is_active ? -1 : 1;
    };

    if (filter === 'all') {
      setFilteredUsers([...users].sort(sortActiveThenAlpha));
    } else if (filter === 'team') {
      if (!selectedTeamId) {
        setFilteredUsers([...users].sort(sortActiveThenAlpha));
      } else {
        setFilteredUsers(users
          .filter(u => {
            if ((u.role || '').toLowerCase() !== 'player') return false;
            if (!u.is_active) return false;
            return String(u.team_id || u.team?.id || '') === String(selectedTeamId);
          })
          .sort(sortActiveThenAlpha));
      }
    } else {
      setFilteredUsers(users
        .filter(u => (u.role || '').toLowerCase() === filter)
        .sort(sortActiveThenAlpha));
    }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ?')) {
      return;
    }

    try {
      await api.delete(`/auth/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
    } catch (err) {
      alert('Erreur lors de la suppression');
      console.error(err);
    }
  };

  const handleEdit = (user) => {
    setEditingUser({
      ...user,
      password: '', // Don't prefill password
    });
  };

  const handleSave = async () => {
    if (!editingUser) return;

    try {
      const updateData = {
        email: editingUser.email,
        full_name: editingUser.full_name,
        role: editingUser.role,
        is_active: editingUser.is_active,
      };

      // Add password only if provided
      if (editingUser.password && editingUser.password.trim() !== '') {
        updateData.password = editingUser.password;
      }

      // Add player fields if role is player
      if (editingUser.role === 'player') {
        updateData.team_id = editingUser.team_id;
        updateData.player_name = editingUser.player_name;
        updateData.age = editingUser.age;

        updateData.position = editingUser.position;
      }

      const response = await api.put(`/auth/users/${editingUser.id}`, updateData);
      
      // Update local state
      setUsers(users.map(u => u.id === editingUser.id ? response.data : u));
      setEditingUser(null);
    } catch (err) {
      console.error('Full error:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Erreur inconnue';
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else {
          errorMessage = JSON.stringify(err.response.data.detail);
        }
      } else if (err.response?.data) {
        errorMessage = JSON.stringify(err.response.data);
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      alert('Erreur lors de la mise à jour: ' + errorMessage);
    }
  };

  const getRoleBadgeColor = (role) => {
    switch ((role || '').toLowerCase()) {
      case 'admin': return 'bg-red-100 text-red-800';
      case 'coach': return 'bg-blue-100 text-blue-800';
      case 'player': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Administration - Gestion des Utilisateurs</h1>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-2 items-center">
          <button
            onClick={() => { setFilter('all'); setSelectedTeamId(''); }}
            className={`px-4 py-2 rounded ${
              filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Tous ({users.length})
          </button>

          <button
            onClick={() => { setFilter('admin'); setSelectedTeamId(''); }}
            className={`px-4 py-2 rounded ${
              filter === 'admin' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Admins ({users.filter(u => u.role === 'admin').length})
          </button>

          <button
            onClick={() => { setFilter('coach'); setSelectedTeamId(''); }}
            className={`px-4 py-2 rounded ${
              filter === 'coach' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Coaches ({users.filter(u => u.role === 'coach').length})
          </button>

          {/* Sélecteur Joueurs + Équipe combiné */}
          <select
            value={ (filter === 'team' ? (selectedTeamId || '') : (filter === 'player' ? 'players_all' : 'all')) }
            onChange={(e) => {
              const val = e.target.value;
              if (val === 'all') {
                setSelectedTeamId('');
                setFilter('all');
              } else if (val === 'players_all') {
                setSelectedTeamId('');
                setFilter('player');
              } else {
                setSelectedTeamId(val);
                setFilter('team');
              }
            }}
            className="px-3 py-2 rounded border bg-white text-gray-700"
          >
            <option value="all">Tous ({users.length})</option>
            <option value="players_all">Joueurs ({users.filter(u => u.role === 'player').length})</option>
            {teams.map(t => (
              <option key={t.id} value={String(t.id)}>
                {`${t.academy?.country?.name || 'unknown'}/${t.academy?.name || 'academy'}/${t.name} (${users.filter(u => (u.role || '').toLowerCase() === 'player' && u.is_active && String(u.team_id || u.team?.id || '') === String(t.id)).length})`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nom
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rôle
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Poste
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Équipe
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Statut
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredUsers.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {u.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {u.email}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button
                    onClick={() => navigate(`/players/${encodeURIComponent(u.player_name || u.full_name)}`)}
                    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium"
                  >
                    {u.full_name}
                  </button>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getRoleBadgeColor(u.role)}`}>
                    {u.role?.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {u.position || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {u.team_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    u.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {u.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  {u.id !== user?.id && (
                    <button
                      onClick={() => handleDelete(u.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Supprimer
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
