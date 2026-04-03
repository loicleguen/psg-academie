import api from './api';

export const catapultService = {
  async uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/catapult/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async getSessions() {
    const response = await api.get('/catapult/sessions');
    return response.data;
  },

  async getSessionByTitle(title) {
    const response = await api.get(`/catapult/sessions/title/${encodeURIComponent(title)}`);
    return response.data;
  },

  async getSessionsByPlayer(playerName) {
    const response = await api.get(`/catapult/sessions/player/${encodeURIComponent(playerName)}`);
    return response.data;
  },

  async deleteSession(sessionTitle) {
    const response = await api.delete(`/catapult/sessions/by-title/${encodeURIComponent(sessionTitle)}`);
    return response.data;
  },

  async analyzeSession(title) {
    const response = await api.post(`/catapult/analyze/session/${encodeURIComponent(title)}`);
    return response.data;
  },

  async generateSessionReport(sessionTitle) {
    const response = await api.post('/catapult/reports/session', null, {
      params: { session_title: sessionTitle }
    });
    return response.data;
  },

  async generatePlayerGraphs(playerName) {
    const response = await api.post(`/catapult/graphs/player/${encodeURIComponent(playerName)}`);
    return response.data;
  },

  async getPlayerStats(playerName) {
    const response = await api.get(`/catapult/players/${encodeURIComponent(playerName)}/stats`);
    return response.data;
  },

  async getAllPlayers() {
    const response = await api.get('/catapult/players');
    return response.data;
  },

  async getSessionPlayersByTitle(sessionTitle) {
    const response = await api.get('/catapult/session-players-by-title', {
      params: { session_title: sessionTitle },
    });
    return response.data;
  },

  async getTeams() {
    const response = await api.get('/teams/');
    return response.data;
  },

  async getTeamPlayers(teamName) {
    const response = await api.get(`/teams/${encodeURIComponent(teamName)}/players`);
    return response.data;
  },
};
