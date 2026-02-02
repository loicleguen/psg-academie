import api from './api';

export const organizationService = {
  // Countries - READ
  async getCountries() {
    const response = await api.get('/countries');
    return response.data;
  },

  async getCountryByName(name) {
    const response = await api.get(`/countries/${name}`);
    return response.data;
  },

  // Countries - CREATE, UPDATE, DELETE
  async createCountry(name) {
    const response = await api.post('/countries', { name });
    return response.data;
  },

  async updateCountry(countryName, newName) {
    const response = await api.put(`/countries/${countryName}`, { name: newName });
    return response.data;
  },

  async deleteCountry(countryName) {
    const response = await api.delete(`/countries/${countryName}`);
    return response.data;
  },

  // Academies - READ
  async getAcademies() {
    const response = await api.get('/academies');
    return response.data;
  },

  async getAcademiesByCountry(countryName) {
    const response = await api.get(`/academies/country/${countryName}`);
    return response.data;
  },

  async getAcademyByName(name) {
    const response = await api.get(`/academies/${name}`);
    return response.data;
  },

  // Academies - CREATE, UPDATE, DELETE
  async createAcademy(name, countryId) {
    const response = await api.post('/academies', { name, country_id: countryId });
    return response.data;
  },

  async updateAcademy(academyName, newName) {
    const response = await api.put(`/academies/${academyName}`, { name: newName });
    return response.data;
  },

  async deleteAcademy(academyName) {
    const response = await api.delete(`/academies/${academyName}`);
    return response.data;
  },

  // Teams - READ
  async getTeams() {
    const response = await api.get('/teams');
    return response.data;
  },

  async getTeamsByAcademy(academyName) {
    const response = await api.get(`/teams/academy/${academyName}`);
    return response.data;
  },

  async getTeamByName(name) {
    const response = await api.get(`/teams/${name}`);
    return response.data;
  },

  async getTeamPlayers(teamName) {
    const response = await api.get(`/teams/${teamName}/players`);
    return response.data;
  },

  // Teams - CREATE, UPDATE, DELETE
  async createTeam(name, academyId) {
    const response = await api.post('/teams', { name, academy_id: academyId });
    return response.data;
  },

  async updateTeam(teamId, newName) {
    const response = await api.put(`/teams/${teamId}`, { name: newName });
    return response.data;
  },

  async deleteTeam(teamId) {
    const response = await api.delete(`/teams/${teamId}`);
    return response.data;
  },
};
