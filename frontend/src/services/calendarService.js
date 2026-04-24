import api from './api';

function compactParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
  );
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const calendarService = {
  async getEvents(filters = {}) {
    const response = await api.get('/calendar/events', {
      params: compactParams(filters),
    });
    return response.data;
  },

  async createEvent(payload) {
    const response = await api.post('/calendar/events', payload);
    return response.data;
  },

  async updateEvent(eventId, payload) {
    const response = await api.patch(`/calendar/events/${eventId}`, payload);
    return response.data;
  },

  async deleteEvent(eventId) {
    const response = await api.delete(`/calendar/events/${eventId}`);
    return response.data;
  },

  async exportIcs(filters = {}) {
    const response = await api.get('/calendar/export.ics', {
      params: compactParams(filters),
      responseType: 'blob',
    });
    downloadBlob(response.data, 'psg-calendar.ics');
  },

  async exportPdf(filters = {}) {
    const response = await api.get('/calendar/export.pdf', {
      params: compactParams(filters),
      responseType: 'blob',
    });
    downloadBlob(response.data, 'psg-calendar.pdf');
  },
};
