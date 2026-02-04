import axios from 'axios';

const api = axios.create({
  baseURL: '/api/physical',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Variable pour éviter les tentatives multiples de refresh en parallèle
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Intercepteur pour ajouter le token JWT
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs 401 (token expiré)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si erreur 401 et qu'on n'a pas déjà tenté de refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Si un refresh est déjà en cours, mettre la requête en attente
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      
      if (!refreshToken) {
        // Pas de refresh token, déconnecter
        isRefreshing = false;
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Tenter de rafraîchir le token
        const response = await api.post('/auth/refresh', null, {
          params: { refresh_token: refreshToken },
          _retry: true // Éviter la boucle infinie
        });

        const newAccessToken = response.data.access_token;
        localStorage.setItem('access_token', newAccessToken);
        
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token);
        }

        // Mettre à jour l'en-tête de la requête originale
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        
        // Traiter les requêtes en attente
        processQueue(null, newAccessToken);
        isRefreshing = false;

        // Réessayer la requête originale
        return api(originalRequest);
      } catch (refreshError) {
        // Le refresh a échoué, déconnecter
        processQueue(refreshError, null);
        isRefreshing = false;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
