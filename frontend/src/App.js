import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard';
import { isAuthenticated, getUser, clearAuthData, isTokenExpired, getAccessToken } from './utils/auth';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const checkAuthStatus = async () => {
      console.log('Checking authentication status...');
      
      try {
        // Check if we have valid authentication
        if (isAuthenticated()) {
          const userData = getUser();
          const accessToken = getAccessToken();
          
          // Double-check token validity
          if (userData && accessToken && !isTokenExpired(accessToken)) {
            console.log('User is authenticated:', userData.username);
            setUser(userData);
          } else {
            console.log('Invalid or expired authentication, clearing data');
            clearAuthData();
            setUser(null);
          }
        } else {
          console.log('User is not authenticated');
          setUser(null);
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
        clearAuthData();
        setUser(null);
      } finally {
        setAuthChecked(true);
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // Set up token expiration monitoring
  useEffect(() => {
    if (!user) return;

    const checkTokenExpiration = () => {
      const accessToken = getAccessToken();
      if (!accessToken || isTokenExpired(accessToken)) {
        console.log('Token expired, logging out user');
        handleLogout();
      }
    };

    // Check token expiration every minute
    const intervalId = setInterval(checkTokenExpiration, 60000);

    return () => clearInterval(intervalId);
  }, [user]);

  const handleLogin = (userData) => {
    console.log('User logged in:', userData.username);
    setUser(userData);
  };

  const handleLogout = () => {
    console.log('User logged out');
    setUser(null);
    clearAuthData();
  };

  // Show loading spinner while checking authentication
  if (loading || !authChecked) {
    return (
      <div className="auth-container">
        <div style={{ textAlign: 'center' }}>
          <div className="loading-spinner" style={{ margin: '0 auto 16px' }}></div>
          <p style={{ color: '#6b7280', fontSize: '14px' }}>
            Checking authentication status...
          </p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/login" 
            element={
              !user ? (
                <Login onLogin={handleLogin} />
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          <Route 
            path="/register" 
            element={
              !user ? (
                <Register onRegister={handleLogin} />
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          <Route 
            path="/dashboard" 
            element={
              user ? (
                <Dashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
          <Route 
            path="/" 
            element={
              <Navigate to={user ? "/dashboard" : "/login"} replace />
            } 
          />
          {/* Catch-all route */}
          <Route 
            path="*" 
            element={
              <Navigate to={user ? "/dashboard" : "/login"} replace />
            } 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 