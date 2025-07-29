import React, { useState, useEffect } from 'react';
import { authAPI, fileAPI } from '../services/api';
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

  // File listing state
  const [files, setFiles] = useState([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [filesError, setFilesError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeSearchTerm, setActiveSearchTerm] = useState('');
  const [sizeMin, setSizeMin] = useState(0);
  const [sizeMax, setSizeMax] = useState(1073741824); // 1GB in bytes
  const [activeSizeMin, setActiveSizeMin] = useState(0);
  const [activeSizeMax, setActiveSizeMax] = useState(1073741824);

  // Fetch fresh user data on component mount
  useEffect(() => {
    fetchUserData();
    fetchFiles();
  }, []);

  // Refetch files when page, page size, or active search/filter terms change
  useEffect(() => {
    fetchFiles();
  }, [currentPage, pageSize, activeSearchTerm, activeSizeMin, activeSizeMax]);

  // Reset to page 1 when active search term or size filters change
  useEffect(() => {
    if (activeSearchTerm !== '' || activeSizeMin > 0 || activeSizeMax < 1073741824) {
      setCurrentPage(1);
    }
  }, [activeSearchTerm, activeSizeMin, activeSizeMax]);

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

  const fetchFiles = async (showLoading = true) => {
    if (showLoading) {
      setIsLoadingFiles(true);
    }
    setFilesError('');

    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        ordering: '-uploaded_at' // Show newest first
      };

      // Add search parameter if search term exists
      if (activeSearchTerm.trim()) {
        params.filename = activeSearchTerm.trim();
      }

      // Add size filter parameters if active
      if (activeSizeMin > 0) {
        params.size_min = activeSizeMin;
      }
      if (activeSizeMax < 1073741824) { // 1GB in bytes
        params.size_max = activeSizeMax;
      }

      const filterDescription = [];
      if (activeSearchTerm) filterDescription.push(`search "${activeSearchTerm}"`);
      if (activeSizeMin > 0) filterDescription.push(`min size ${formatBytesShort(activeSizeMin)}`);
      if (activeSizeMax < 1073741824) filterDescription.push(`max size ${formatBytesShort(activeSizeMax)}`);
      
      console.log(`Fetching files page ${currentPage} with size ${pageSize}${filterDescription.length ? ` and filters: ${filterDescription.join(', ')}` : ''}...`);
      const response = await fileAPI.getFiles(params);
      
      const data = response.data;
      console.log('Files received:', data);
      
      setFiles(data.results || []);
      setTotalFiles(data.count || 0);
      setTotalPages(Math.ceil((data.count || 0) / pageSize));
      setHasNext(!!data.next);
      setHasPrevious(!!data.previous);
      
    } catch (error) {
      console.error('Failed to fetch files:', error);
      
      if (error.response?.status === 401) {
        setFilesError('Session expired. Please log in again.');
      } else if (error.type === 'network_error') {
        setFilesError('Network error. Could not load files.');
      } else {
        setFilesError('Failed to load files. Please try again.');
      }
    } finally {
      if (showLoading) {
        setIsLoadingFiles(false);
      }
    }
  };

  const handleRefreshUserData = () => {
    fetchUserData(true);
  };

  const handleRefreshFiles = () => {
    fetchFiles(true);
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
    
    // Refresh files list and go to first page to see new file
    setCurrentPage(1);
    fetchFiles(false);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handlePageSizeChange = (newPageSize) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleSearch = () => {
    setActiveSearchTerm(searchTerm.trim());
    setActiveSizeMin(sizeMin);
    setActiveSizeMax(sizeMax);
    setCurrentPage(1);
  };

  const handleSearchKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    setActiveSearchTerm('');
    setSizeMin(0);
    setSizeMax(1073741824);
    setActiveSizeMin(0);
    setActiveSizeMax(1073741824);
    setCurrentPage(1);
  };

  const handleSizeMinChange = (e) => {
    const value = parseInt(e.target.value);
    setSizeMin(value);
    // Ensure min doesn't exceed max
    if (value > sizeMax) {
      setSizeMax(value);
    }
  };

  const handleSizeMaxChange = (e) => {
    const value = parseInt(e.target.value);
    setSizeMax(value);
    // Ensure max doesn't go below min
    if (value < sizeMin) {
      setSizeMin(value);
    }
  };

  const formatBytesShort = (bytes) => {
    if (bytes === 0) return '0';
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}KB`;
    if (bytes < 1024 * 1024 * 1024) return `${Math.round(bytes / (1024 * 1024))}MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}GB`;
  };

  const hasActiveFilters = () => {
    return activeSearchTerm !== '' || activeSizeMin > 0 || activeSizeMax < 1073741824;
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
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStoragePercentage = () => {
    if (!currentUser?.storage_quota || currentUser.storage_quota === 0) return 0;
    return Math.round((currentUser.storage_used / currentUser.storage_quota) * 100);
  };

  const getMimeTypeIcon = (mimeType) => {
    if (!mimeType) return '📄';
    
    if (mimeType.startsWith('image/')) return '🖼️';
    if (mimeType.startsWith('video/')) return '🎥';
    if (mimeType.startsWith('audio/')) return '🎵';
    if (mimeType.includes('pdf')) return '📕';
    if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
    if (mimeType.includes('sheet') || mimeType.includes('excel')) return '📊';
    if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📽️';
    if (mimeType.includes('zip') || mimeType.includes('archive')) return '📦';
    if (mimeType.includes('text/')) return '📄';
    
    return '📄';
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
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          marginBottom: '32px'
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

        {/* Files List Section */}
        <div style={{ 
          background: 'white', 
          borderRadius: '12px', 
          padding: '32px', 
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 style={{ 
              fontSize: '24px', 
              fontWeight: '700', 
              color: '#1f2937', 
              margin: 0
            }}>
              Your Files
            </h2>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              {/* Search Input */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '200px' }}>
                <div style={{ position: 'relative', flex: 1 }}>
                  <input
                    type="text"
                    placeholder="Search by filename"
                    value={searchTerm}
                    onChange={handleSearchChange}
                    onKeyPress={handleSearchKeyPress}
                    disabled={isLoadingFiles}
                    style={{
                      width: '100%',
                      padding: '6px 80px 6px 12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      fontSize: '14px',
                      backgroundColor: isLoadingFiles ? '#f3f4f6' : 'white'
                    }}
                  />
                  <div style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    display: 'flex',
                    gap: '4px',
                    alignItems: 'center'
                  }}>
                    <button
                      onClick={handleSearch}
                      disabled={isLoadingFiles}
                      style={{
                        background: isLoadingFiles ? '#9ca3af' : '#667eea',
                        border: 'none',
                        color: 'white',
                        cursor: isLoadingFiles ? 'not-allowed' : 'pointer',
                        fontSize: '11px',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontWeight: '500'
                      }}
                      title="Apply filters"
                    >
                      {isLoadingFiles ? (
                        <div className="loading-spinner" style={{ width: '10px', height: '10px' }}></div>
                      ) : (
                        'Filter'
                      )}
                    </button>
                    {(searchTerm || activeSearchTerm || sizeMin > 0 || sizeMax < 1073741824) && (
                      <button
                        onClick={handleClearSearch}
                        disabled={isLoadingFiles}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#6b7280',
                          cursor: isLoadingFiles ? 'not-allowed' : 'pointer',
                          fontSize: '16px',
                          padding: '2px',
                          borderRadius: '2px'
                        }}
                        title="Clear all filters"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Size Filter Sliders */}
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '8px', 
                minWidth: '200px',
                padding: '8px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#f9fafb'
              }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '4px' }}>
                  File Size Filter
                </div>
                
                {/* Min Size Slider */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '11px', color: '#6b7280' }}>Min:</label>
                    <span style={{ fontSize: '11px', color: '#374151', fontWeight: '500' }}>
                      {formatBytesShort(sizeMin)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1073741824"
                    step="1048576"
                    value={sizeMin}
                    onChange={handleSizeMinChange}
                    disabled={isLoadingFiles}
                    style={{
                      width: '100%',
                      height: '4px',
                      borderRadius: '2px',
                      background: `linear-gradient(to right, #667eea 0%, #667eea ${(sizeMin / 1073741824) * 100}%, #e5e7eb ${(sizeMin / 1073741824) * 100}%, #e5e7eb 100%)`,
                      outline: 'none',
                      WebkitAppearance: 'none',
                      cursor: isLoadingFiles ? 'not-allowed' : 'pointer'
                    }}
                  />
                </div>

                {/* Max Size Slider */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '11px', color: '#6b7280' }}>Max:</label>
                    <span style={{ fontSize: '11px', color: '#374151', fontWeight: '500' }}>
                      {formatBytesShort(sizeMax)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1073741824"
                    step="1048576"
                    value={sizeMax}
                    onChange={handleSizeMaxChange}
                    disabled={isLoadingFiles}
                    style={{
                      width: '100%',
                      height: '4px',
                      borderRadius: '2px',
                      background: `linear-gradient(to right, #667eea 0%, #667eea ${(sizeMax / 1073741824) * 100}%, #e5e7eb ${(sizeMax / 1073741824) * 100}%, #e5e7eb 100%)`,
                      outline: 'none',
                      WebkitAppearance: 'none',
                      cursor: isLoadingFiles ? 'not-allowed' : 'pointer'
                    }}
                  />
                </div>
              </div>

              {/* Page Size Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '14px', color: '#6b7280' }}>Show:</span>
                <select
                  value={pageSize}
                  onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                  disabled={isLoadingFiles}
                  style={{
                    padding: '4px 8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                    backgroundColor: isLoadingFiles ? '#f3f4f6' : 'white'
                  }}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
                <span style={{ fontSize: '14px', color: '#6b7280' }}>per page</span>
              </div>
              
              <button 
                onClick={handleRefreshFiles}
                disabled={isLoadingFiles}
                style={{
                  padding: '6px 12px',
                  background: isLoadingFiles ? '#9ca3af' : '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: isLoadingFiles ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                {isLoadingFiles ? (
                  <>
                    <div className="loading-spinner" style={{ width: '12px', height: '12px' }}></div>
                    Loading...
                  </>
                ) : (
                  '🔄 Refresh'
                )}
              </button>
            </div>
          </div>

          {/* Files Error */}
          {filesError && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '20px',
              color: '#dc2626',
              fontSize: '14px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>{filesError}</span>
              <button 
                onClick={handleRefreshFiles}
                style={{
                  padding: '4px 8px',
                  background: '#dc2626',
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

                     {/* Search/Filter Results Info */}
          {hasActiveFilters() && !isLoadingFiles && (
            <div style={{
              background: '#f0f9ff',
              border: '1px solid #bae6fd',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '14px',
              color: '#0c4a6e'
            }}>
              {files.length > 0 ? (
                <>
                  Found <strong>{totalFiles}</strong> file{totalFiles !== 1 ? 's' : ''} with filters:
                  {activeSearchTerm && <span> filename "<strong>{activeSearchTerm}</strong>"</span>}
                  {activeSizeMin > 0 && <span> min size <strong>{formatBytesShort(activeSizeMin)}</strong></span>}
                  {activeSizeMax < 1073741824 && <span> max size <strong>{formatBytesShort(activeSizeMax)}</strong></span>}
                  <button
                    onClick={handleClearSearch}
                    style={{
                      marginLeft: '12px',
                      padding: '2px 8px',
                      background: '#0ea5e9',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    Clear filters
                  </button>
                </>
              ) : (
                <>
                  No files found with current filters
                  <button
                    onClick={handleClearSearch}
                    style={{
                      marginLeft: '12px',
                      padding: '2px 8px',
                      background: '#0ea5e9',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    Clear filters
                  </button>
                </>
              )}
            </div>
          )}

          {/* Files List */}
          {isLoadingFiles ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div className="loading-spinner" style={{ margin: '0 auto 16px' }}></div>
              <p style={{ color: '#6b7280', fontSize: '14px' }}>
                {hasActiveFilters() ? 'Applying filters...' : 'Loading your files...'}
              </p>
            </div>
          ) : files.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>
                {hasActiveFilters() ? '🔍' : '📁'}
              </div>
              <h3 style={{ color: '#374151', marginBottom: '8px' }}>
                {hasActiveFilters() ? 'No files found' : 'No files yet'}
              </h3>
              <p style={{ color: '#6b7280', fontSize: '14px' }}>
                {hasActiveFilters() 
                  ? 'No files match your current filters. Try adjusting your search criteria.'
                  : 'Upload your first file to get started!'
                }
              </p>
            </div>
          ) : (
            <>
              {/* Files Table */}
              <div style={{ 
                border: '1px solid #e5e7eb', 
                borderRadius: '8px', 
                overflow: 'hidden',
                marginBottom: '24px'
              }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '60px 1fr 120px 120px 180px',
                  gap: '16px',
                  padding: '16px',
                  backgroundColor: '#f9fafb',
                  borderBottom: '1px solid #e5e7eb',
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#374151'
                }}>
                  <div>Type</div>
                  <div>Name</div>
                  <div>Size</div>
                  <div>Tags</div>
                  <div>Uploaded</div>
                </div>
                
                {files.map((file) => (
                  <div
                    key={file.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '60px 1fr 120px 120px 180px',
                      gap: '16px',
                      padding: '16px',
                      borderBottom: files.indexOf(file) < files.length - 1 ? '1px solid #f3f4f6' : 'none',
                      fontSize: '14px',
                      alignItems: 'center'
                    }}
                  >
                    <div style={{ fontSize: '24px' }}>
                      {getMimeTypeIcon(file.mime_type)}
                    </div>
                    <div style={{ 
                      fontWeight: '500', 
                      color: '#374151',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {file.original_filename}
                    </div>
                    <div style={{ color: '#6b7280' }}>
                      {formatBytes(file.size)}
                    </div>
                    <div style={{ color: '#6b7280' }}>
                      {file.tags && file.tags.length > 0 ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          {file.tags.slice(0, 2).map((tag, index) => (
                            <span
                              key={index}
                              style={{
                                padding: '2px 6px',
                                backgroundColor: '#e0e7ff',
                                color: '#3730a3',
                                borderRadius: '12px',
                                fontSize: '11px',
                                fontWeight: '500'
                              }}
                            >
                              {tag}
                            </span>
                          ))}
                          {file.tags.length > 2 && (
                            <span style={{ fontSize: '11px', color: '#9ca3af' }}>
                              +{file.tags.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: '#d1d5db' }}>—</span>
                      )}
                    </div>
                    <div style={{ color: '#6b7280' }}>
                      {formatDate(file.uploaded_at)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '16px 0'
                }}>
                                     <div style={{ fontSize: '14px', color: '#6b7280' }}>
                     Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalFiles)} of {totalFiles} files
                     {hasActiveFilters() && (
                       <span style={{ fontStyle: 'italic' }}> (filtered)</span>
                     )}
                   </div>
                  
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        handlePageChange(currentPage - 1);
                      }}
                      disabled={!hasPrevious || isLoadingFiles}
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '6px',
                        background: (!hasPrevious || isLoadingFiles) ? '#f9fafb' : 'white',
                        color: (!hasPrevious || isLoadingFiles) ? '#9ca3af' : '#374151',
                        fontSize: '14px',
                        cursor: (!hasPrevious || isLoadingFiles) ? 'not-allowed' : 'pointer'
                      }}
                    >
                      ← Previous
                    </button>
                    
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (currentPage <= 3) {
                          pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = currentPage - 2 + i;
                        }
                        
                        return (
                          <button
                            key={pageNum}
                            onClick={(e) => {
                              e.preventDefault();
                              handlePageChange(pageNum);
                            }}
                            disabled={isLoadingFiles}
                            style={{
                              padding: '8px 12px',
                              border: '1px solid #d1d5db',
                              borderRadius: '6px',
                              background: pageNum === currentPage ? '#667eea' : 'white',
                              color: pageNum === currentPage ? 'white' : '#374151',
                              fontSize: '14px',
                              cursor: isLoadingFiles ? 'not-allowed' : 'pointer',
                              minWidth: '40px'
                            }}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>
                    
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        handlePageChange(currentPage + 1);
                      }}
                      disabled={!hasNext || isLoadingFiles}
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '6px',
                        background: (!hasNext || isLoadingFiles) ? '#f9fafb' : 'white',
                        color: (!hasNext || isLoadingFiles) ? '#9ca3af' : '#374151',
                        fontSize: '14px',
                        cursor: (!hasNext || isLoadingFiles) ? 'not-allowed' : 'pointer'
                      }}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
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