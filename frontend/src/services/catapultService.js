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

  async analyzeSession(title) {
    const response = await api.post(`/catapult/analyze/session/${encodeURIComponent(title)}`);
    return response.data;
  },

  async generatePlayerGraphs(playerName) {
    const response = await api.post(`/catapult/graphs/player/${encodeURIComponent(playerName)}`);
    return response.data;
  },
};
