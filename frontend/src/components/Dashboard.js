import React from 'react';
import { authAPI } from '../services/api';
import { removeAuthTokens, getRefreshToken } from '../utils/auth';

const Dashboard = ({ user, onLogout }) => {
  const handleLogout = async () => {
    try {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        await authAPI.logout(refreshToken);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      removeAuthTokens();
      onLogout();
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
              <button onClick={handleLogout} className="btn-logout">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="container" style={{ paddingTop: '40px' }}>
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
            border: '1px solid #e5e7eb' 
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
            marginTop: '24px', 
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