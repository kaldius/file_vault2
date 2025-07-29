import React, { useState } from 'react';
import { authAPI } from '../services/api';
import { removeAuthTokens, getRefreshToken } from '../utils/auth';

const Dashboard = ({ user, onLogout }) => {
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');

  const handleLogout = async () => {
    if (isLoggingOut) return; // Prevent double-clicks
    
    setIsLoggingOut(true);
    setLogoutError('');

    try {
      const refreshToken = getRefreshToken();
      console.log('Starting logout process...');
      
      if (refreshToken) {
        // Call logout API to blacklist the refresh token
        await authAPI.logout(refreshToken);
      } else {
        console.warn('No refresh token found, proceeding with local logout');
      }
      
      console.log('Logout completed successfully');
      
      // Clear local storage and update app state
      removeAuthTokens();
      onLogout();
      
    } catch (error) {
      console.error('Logout error:', error);
      
      // Set user-friendly error message
      if (error.type === 'network_error') {
        setLogoutError('Network error during logout. You have been logged out locally.');
      } else {
        setLogoutError('Logout failed on server, but you have been logged out locally.');
      }
      
      // Even if logout API fails, clear local data and log out
      removeAuthTokens();
      
      // Show error briefly then complete logout
      setTimeout(() => {
        onLogout();
      }, 2000);
      
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleManualTokenRefresh = async () => {
    try {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        await authAPI.refreshToken(refreshToken);
        console.log('Token refreshed manually');
      }
    } catch (error) {
      console.error('Manual token refresh failed:', error);
    }
  };

  return (
    <div className="dashboard">
      <nav className="navbar">
        <div className="container">
          <div className="navbar-content">
            <div className="navbar-brand">File Vault</div>
            <div className="navbar-user">
              <div className="user-info">
                Welcome, {user.first_name} {user.last_name}
              </div>
              <button 
                onClick={handleLogout} 
                className="btn-logout"
                disabled={isLoggingOut}
              >
                {isLoggingOut ? (
                  <>
                    <div className="loading-spinner" style={{ width: '12px', height: '12px' }}></div>
                    Logging out...
                  </>
                ) : (
                  'Logout'
                )}
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="container" style={{ paddingTop: '40px' }}>
        {logoutError && (
          <div style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '20px',
            color: '#dc2626',
            fontSize: '14px'
          }}>
            {logoutError}
          </div>
        )}
        
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '32px', 
          textAlign: 'center',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}>
          <h1 style={{ 
            fontSize: '32px', 
            fontWeight: '700', 
            color: '#1f2937', 
            marginBottom: '16px' 
          }}>
            Welcome to File Vault!
          </h1>
          <p style={{ 
            fontSize: '18px', 
            color: '#6b7280', 
            marginBottom: '32px' 
          }}>
            Your secure file storage system is ready to use.
          </p>
          
          <div style={{ 
            background: '#f8fafc', 
            borderRadius: '8px', 
            padding: '24px', 
            border: '1px solid #e5e7eb',
            marginBottom: '24px'
          }}>
            <h2 style={{ 
              fontSize: '20px', 
              fontWeight: '600', 
              color: '#374151', 
              marginBottom: '16px' 
            }}>
              Account Information
            </h2>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: '16px',
              textAlign: 'left' 
            }}>
              <div>
                <strong>Username:</strong> {user.username}
              </div>
              <div>
                <strong>Email:</strong> {user.email}
              </div>
              <div>
                <strong>Storage Quota:</strong> {Math.round(user.storage_quota / (1024 * 1024 * 1024))} GB
              </div>
              <div>
                <strong>Storage Used:</strong> {Math.round(user.storage_used / (1024 * 1024))} MB
              </div>
            </div>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
            gap: '16px',
            marginBottom: '24px'
          }}>
            <div style={{ 
              background: '#dbeafe', 
              borderRadius: '8px',
              padding: '16px',
              border: '1px solid #93c5fd'
            }}>
              <h3 style={{ color: '#1e40af', fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                🔐 Authentication Status
              </h3>
              <p style={{ color: '#1e40af', fontSize: '14px', marginBottom: '12px' }}>
                You are securely logged in with JWT tokens
              </p>
              <button 
                onClick={handleManualTokenRefresh}
                style={{
                  padding: '6px 12px',
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Refresh Token
              </button>
            </div>

            <div style={{ 
              background: '#ecfdf5', 
              borderRadius: '8px',
              padding: '16px',
              border: '1px solid #86efac'
            }}>
              <h3 style={{ color: '#059669', fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                🚀 System Status
              </h3>
              <p style={{ color: '#059669', fontSize: '14px' }}>
                All systems operational<br/>
                Backend API connected<br/>
                Database accessible
              </p>
            </div>
          </div>
          
          <div style={{ 
            padding: '16px', 
            background: '#dbeafe', 
            borderRadius: '8px',
            border: '1px solid #93c5fd'
          }}>
            <p style={{ color: '#1e40af', fontSize: '14px' }}>
              🚧 File management features are coming soon! For now, you can register and login to your account.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 