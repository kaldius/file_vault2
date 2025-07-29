// Authentication utility functions

export const setAuthTokens = (accessToken, refreshToken) => {
  if (!accessToken || !refreshToken) {
    console.error('Invalid tokens provided to setAuthTokens');
    return false;
  }
  
  try {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    console.log('Auth tokens stored successfully');
    return true;
  } catch (error) {
    console.error('Failed to store auth tokens:', error);
    return false;
  }
};

export const getAccessToken = () => {
  try {
    return localStorage.getItem('access_token');
  } catch (error) {
    console.error('Failed to retrieve access token:', error);
    return null;
  }
};

export const getRefreshToken = () => {
  try {
    return localStorage.getItem('refresh_token');
  } catch (error) {
    console.error('Failed to retrieve refresh token:', error);
    return null;
  }
};

export const removeAuthTokens = () => {
  try {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    console.log('Auth tokens removed successfully');
    return true;
  } catch (error) {
    console.error('Failed to remove auth tokens:', error);
    return false;
  }
};

export const setUser = (user) => {
  if (!user || typeof user !== 'object') {
    console.error('Invalid user data provided to setUser');
    return false;
  }
  
  try {
    localStorage.setItem('user', JSON.stringify(user));
    console.log('User data stored successfully');
    return true;
  } catch (error) {
    console.error('Failed to store user data:', error);
    return false;
  }
};

export const getUser = () => {
  try {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  } catch (error) {
    console.error('Failed to retrieve user data:', error);
    // If user data is corrupted, remove it
    try {
      localStorage.removeItem('user');
    } catch (removeError) {
      console.error('Failed to remove corrupted user data:', removeError);
    }
    return null;
  }
};

export const isAuthenticated = () => {
  const accessToken = getAccessToken();
  const user = getUser();
  
  if (!accessToken || !user) {
    return false;
  }
  
  // Basic token validation (check if it's not obviously invalid)
  try {
    const parts = accessToken.split('.');
    if (parts.length !== 3) {
      console.warn('Invalid JWT token format');
      return false;
    }
    
    // Decode the payload to check expiration (basic check)
    const payload = JSON.parse(atob(parts[1]));
    const currentTime = Math.floor(Date.now() / 1000);
    
    // If token is expired, consider user not authenticated
    if (payload.exp && payload.exp < currentTime) {
      console.warn('Access token has expired');
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Token validation failed:', error);
    return false;
  }
};

export const isTokenExpired = (token) => {
  if (!token) return true;
  
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    
    const payload = JSON.parse(atob(parts[1]));
    const currentTime = Math.floor(Date.now() / 1000);
    
    return payload.exp ? payload.exp < currentTime : false;
  } catch (error) {
    console.error('Failed to check token expiration:', error);
    return true;
  }
};

export const getTokenExpirationTime = (token) => {
  if (!token) return null;
  
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    
    const payload = JSON.parse(atob(parts[1]));
    return payload.exp ? new Date(payload.exp * 1000) : null;
  } catch (error) {
    console.error('Failed to get token expiration time:', error);
    return null;
  }
};

export const clearAuthData = () => {
  console.log('Clearing all authentication data...');
  return removeAuthTokens();
}; 