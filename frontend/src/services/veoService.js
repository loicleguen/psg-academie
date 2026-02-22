import axios from 'axios';

const tacticalApi = axios.create({
  baseURL: '/api/tactical',
  headers: {
    'Content-Type': 'application/json',
  },
});

tacticalApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const veoService = {
  async getSeasons() {
    const response = await tacticalApi.get('/seasons');
    return response.data;
  },

  async createSeason(payload) {
    const response = await tacticalApi.post('/seasons', payload);
    return response.data;
  },

  async getTeams() {
    const response = await tacticalApi.get('/teams');
    return response.data;
  },

  async createTeam(payload) {
    const response = await tacticalApi.post('/teams', payload);
    return response.data;
  },

  async getPlayers(teamId) {
    const response = await tacticalApi.get('/players', {
      params: teamId ? { team_id: teamId } : {},
    });
    return response.data;
  },

  async createPlayer(payload) {
    const response = await tacticalApi.post('/players', payload);
    return response.data;
  },

  async getMatches(filters = {}) {
    const response = await tacticalApi.get('/matches', {
      params: filters,
    });
    return response.data;
  },

  async getMatchesByDate(date) {
    return this.getMatches({
      from: date,
      to: date,
    });
  },

  async createMatch(payload) {
    const response = await tacticalApi.post('/matches', payload);
    return response.data;
  },

  async bootstrapFromCatapultSession(payload) {
    const response = await tacticalApi.post('/matches/bootstrap-from-catapult', payload);
    return response.data;
  },

  async getMatchParticipations(matchId) {
    const response = await tacticalApi.get(`/matches/${matchId}/participations`);
    return response.data;
  },

  async updateMatchParticipations(matchId, participations) {
    const response = await tacticalApi.put(`/matches/${matchId}/participations`, {
      participations,
    });
    return response.data;
  },

  async getMatchSummary(matchId) {
    const response = await tacticalApi.get(`/matches/${matchId}/summary`);
    return response.data;
  },

  async getEntrySchema(includeDerived = false) {
    const response = await tacticalApi.get('/metrics/entry-schema', {
      params: {
        include_derived: includeDerived,
      },
    });
    return response.data;
  },

  async getTeamMetrics(matchId) {
    const response = await tacticalApi.get(`/metrics/matches/${matchId}/team-metrics`);
    return response.data;
  },

  async updateTeamMetrics(matchId, values) {
    const response = await tacticalApi.put(`/metrics/matches/${matchId}/team-metrics`, {
      values,
    });
    return response.data;
  },

  async getPlayerMetrics(matchId) {
    const response = await tacticalApi.get(`/metrics/matches/${matchId}/player-metrics`);
    return response.data;
  },

  async updatePlayerMetrics(matchId, values) {
    const response = await tacticalApi.put(`/metrics/matches/${matchId}/player-metrics`, {
      values,
    });
    return response.data;
  },
};