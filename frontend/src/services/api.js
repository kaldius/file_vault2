import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    
    // Handle network errors
    if (!error.response) {
      console.error('Network error:', error.message);
      return Promise.reject({
        message: 'Network error. Please check your connection.',
        type: 'network_error'
      });
    }
    
    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      original._retry = true;
      isRefreshing = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (!refreshToken) {
        console.warn('No refresh token available');
        handleAuthFailure();
        return Promise.reject(error);
      }

      try {
        console.log('Attempting to refresh access token...');
        const response = await axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
          refresh: refreshToken,
        });
        
        const { access, refresh } = response.data;
        
        // Update stored tokens
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        
        // Update default header
        api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
        original.headers.Authorization = `Bearer ${access}`;
        
        processQueue(null, access);
        console.log('Token refreshed successfully');
        
        return api(original);
        
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        processQueue(refreshError, null);
        handleAuthFailure();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

// Helper function to handle authentication failures
const handleAuthFailure = () => {
  // Clear all auth data
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  
  // Only redirect if not already on login page
  if (window.location.pathname !== '/login') {
    console.log('Authentication failed, redirecting to login...');
    window.location.href = '/login';
  }
};

// Auth API
export const authAPI = {
  register: (userData) => api.post('/api/auth/register/', userData),
  
  login: async (credentials) => {
    try {
      const response = await api.post('/api/auth/login/', credentials);
      const { access } = response.data;
      
      // Update default header for subsequent requests
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      
      return response;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  },
  
  logout: async (refreshToken) => {
    try {
      if (!refreshToken) {
        console.warn('No refresh token provided for logout');
        return;
      }
      
      console.log('Logging out user...');
      await api.post('/api/auth/logout/', { refresh: refreshToken });
      console.log('Logout successful');
      
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Don't throw error - we still want to clear local data
    } finally {
      // Always clear local auth data regardless of API call success
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      delete api.defaults.headers.common['Authorization'];
    }
  },
  
  refreshToken: async (refreshToken) => {
    try {
      console.log('Manual token refresh requested');
      const response = await api.post('/api/auth/token/refresh/', { refresh: refreshToken });
      
      const { access, refresh } = response.data;
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
      
      return response;
    } catch (error) {
      console.error('Manual token refresh failed:', error);
      handleAuthFailure();
      throw error;
    }
  },
  
  getCurrentUser: () => api.get('/api/users/me/'),
};

// File API (for future use)
export const fileAPI = {
  getFiles: (params) => api.get('/api/files/', { params }),
  getFileDetails: (fileId) => api.get(`/api/files/${fileId}/`),
  uploadFile: (formData) => api.post('/api/files/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  downloadFile: (fileId) => api.get(`/api/files/${fileId}/download/`, {
    responseType: 'blob',
  }),
  deleteFile: (fileId) => api.delete(`/api/files/${fileId}/delete/`),
  getFileStats: () => api.get('/api/files/stats/'),
};

// Utility function to check if user is authenticated
export const checkAuthStatus = () => {
  const token = localStorage.getItem('access_token');
  const user = localStorage.getItem('user');
  return !!(token && user);
};

export default api; 