import axios from 'axios';

const API_URL = 'http://localhost:8000/api/meetings';

export const validateToken = async () => {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) return false;

    const response = await axios.get(`${API_URL}/validate-token/`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    return response.data.valid;
  } catch (error) {
    return false;
  }
};

export const refreshToken = async () => {
  try {
    const refresh_token = localStorage.getItem('refresh_token');
    if (!refresh_token) return false;

    const response = await axios.post(`${API_URL}/refresh-token/`, {
      refresh: refresh_token
    });

    if (response.data.success) {
      localStorage.setItem('access_token', response.data.token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
      return true;
    }
    return false;
  } catch (error) {
    return false;
  }
};

export const setupAxiosInterceptors = () => {
  // Request interceptor
  axios.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor
  axios.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      // If the error is 401 and we haven't tried to refresh the token yet
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        // Try to refresh the token
        const refreshed = await refreshToken();
        if (refreshed) {
          // Retry the original request
          return axios(originalRequest);
        }
      }

      return Promise.reject(error);
    }
  );
}; 