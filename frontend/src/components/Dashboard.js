import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { removeAuthTokens, getRefreshToken, setUser } from '../utils/auth';
import FileUploadModal from './FileUploadModal';

const Dashboard = ({ user, onLogout }) => {
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  const [currentUser, setCurrentUser] = useState(user);
  const [isLoadingUser, setIsLoadingUser] = useState(false);
  const [userError, setUserError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);

  // Fetch fresh user data on component mount
  useEffect(() => {
    fetchUserData();
  }, []);

  // Clear upload success message after 5 seconds
  useEffect(() => {
    if (uploadSuccess) {
      const timer = setTimeout(() => {
        setUploadSuccess(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [uploadSuccess]);

  const fetchUserData = async (showLoading = true) => {
    if (showLoading) {
      setIsLoadingUser(true);
    }
    setUserError('');

    try {
      console.log('Fetching fresh user data from /api/users/me...');
      const response = await authAPI.getCurrentUser();
      const userData = response.data;
      
      console.log('Fresh user data received:', userData);
      
      // Update local state
      setCurrentUser(userData);
      setLastUpdated(new Date());
      
      // Update stored user data
      setUser(userData);
      
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      
      if (error.response?.status === 401) {
        setUserError('Session expired. Please log in again.');
        // Don't automatically logout here as the token refresh should handle this
      } else if (error.type === 'network_error') {
        setUserError('Network error. Using cached user data.');
      } else {
        setUserError('Failed to load user data. Using cached information.');
      }
    } finally {
      if (showLoading) {
        setIsLoadingUser(false);
      }
    }
  };

  const handleRefreshUserData = () => {
    fetchUserData(true);
  };

  const handleUploadSuccess = (uploadedFile) => {
    console.log('File uploaded successfully:', uploadedFile);
    
    // Show success message
    setUploadSuccess({
      filename: uploadedFile.original_filename,
      size: uploadedFile.size,
      timestamp: new Date()
    });
    
    // Refresh user data to get updated storage usage
    fetchUserData(false);
  };

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
        // Fetch fresh user data after token refresh
        fetchUserData(false);
      }
    } catch (error) {
      console.error('Manual token refresh failed:', error);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStoragePercentage = () => {
    if (!currentUser?.storage_quota || currentUser.storage_quota === 0) return 0;
    return Math.round((currentUser.storage_used / currentUser.storage_quota) * 100);
  };

  const displayUser = currentUser || user;

  return (
    <div className="dashboard">
      <nav className="navbar">
        <div className="container">
          <div className="navbar-content">
            <div className="navbar-brand">File Vault</div>
            <div className="navbar-user">
              <div className="user-info">
                Welcome, {displayUser.first_name} {displayUser.last_name}
                {isLoadingUser && (
                  <div className="loading-spinner" style={{ 
                    width: '12px', 
                    height: '12px', 
                    marginLeft: '8px', 
                    display: 'inline-block' 
                  }}></div>
                )}
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

        {userError && (
          <div style={{
            background: '#fef3cd',
            border: '1px solid #fde047',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '20px',
            color: '#d97706',
            fontSize: '14px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>{userError}</span>
            <button 
              onClick={handleRefreshUserData}
              style={{
                padding: '4px 8px',
                background: '#d97706',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        )}

        {uploadSuccess && (
          <div style={{
            background: '#ecfdf5',
            border: '1px solid #86efac',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '20px',
            color: '#059669',
            fontSize: '14px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <strong>✅ Upload Successful!</strong>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                {uploadSuccess.filename} ({formatBytes(uploadSuccess.size)}) uploaded at {uploadSuccess.timestamp.toLocaleTimeString()}
              </div>
            </div>
            <button 
              onClick={() => setUploadSuccess(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#059669',
                cursor: 'pointer',
                fontSize: '16px',
                padding: '4px'
              }}
            >
              ×
            </button>
          </div>
        )}
        
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '32px', 
          textAlign: 'center',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h1 style={{ 
              fontSize: '32px', 
              fontWeight: '700', 
              color: '#1f2937', 
              margin: 0
            }}>
              Welcome to File Vault!
            </h1>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                onClick={() => setIsUploadModalOpen(true)}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: '500'
                }}
              >
                📤 Upload File
              </button>
              <button 
                onClick={handleRefreshUserData}
                disabled={isLoadingUser}
                style={{
                  padding: '8px 16px',
                  background: isLoadingUser ? '#9ca3af' : '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: isLoadingUser ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {isLoadingUser ? (
                  <>
                    <div className="loading-spinner" style={{ width: '14px', height: '14px' }}></div>
                    Updating...
                  </>
                ) : (
                  '🔄 Refresh Data'
                )}
              </button>
            </div>
          </div>

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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ 
                fontSize: '20px', 
                fontWeight: '600', 
                color: '#374151', 
                margin: 0
              }}>
                Account Information
              </h2>
              {lastUpdated && (
                <span style={{ fontSize: '12px', color: '#6b7280' }}>
                  Last updated: {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>
            
            <div style={{ 
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              textAlign: 'left',
              marginBottom: '20px'
            }}>
              <div>
                <strong>Username:</strong> {displayUser.username}
              </div>
              <div>
                <strong>Email:</strong> {displayUser.email}
              </div>
              <div>
                <strong>Member Since:</strong> {formatDate(displayUser.created_at)}
              </div>
            </div>

            {/* Storage Usage Visualization */}
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: '600', color: '#374151' }}>Storage Usage</span>
                <span style={{ fontSize: '14px', color: '#6b7280' }}>
                  {formatBytes(displayUser.storage_used)} / {formatBytes(displayUser.storage_quota)} 
                  ({getStoragePercentage()}%)
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '12px',
                backgroundColor: '#e5e7eb',
                borderRadius: '6px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${Math.min(getStoragePercentage(), 100)}%`,
                  height: '100%',
                  backgroundColor: getStoragePercentage() > 90 ? '#ef4444' : getStoragePercentage() > 75 ? '#f59e0b' : '#10b981',
                  transition: 'width 0.3s ease'
                }}></div>
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
            background: '#ecfdf5', 
            borderRadius: '8px',
            border: '1px solid #86efac'
          }}>
            <p style={{ color: '#059669', fontSize: '14px' }}>
              🎉 File upload is now available! Click the "Upload File" button above to get started.
            </p>
          </div>
        </div>
      </div>

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};

export default Dashboard; 