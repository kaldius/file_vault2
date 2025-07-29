import React, { useState, useEffect } from 'react';
import { fileAPI } from '../services/api';

const FileDetailsModal = ({ isOpen, onClose, fileId, onFileDeleted }) => {
  const [fileDetails, setFileDetails] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch file details when modal opens
  useEffect(() => {
    if (isOpen && fileId) {
      fetchFileDetails();
    }
  }, [isOpen, fileId]);

  const fetchFileDetails = async () => {
    setIsLoading(true);
    setError('');
    setFileDetails(null);

    try {
      console.log(`Fetching details for file ID: ${fileId}`);
      const response = await fileAPI.getFileDetails(fileId);
      
      console.log('File details received:', response.data);
      setFileDetails(response.data);
    } catch (error) {
      console.error('Failed to fetch file details:', error);
      
      if (error.response?.status === 404) {
        setError('File not found or you do not have permission to view it.');
      } else if (error.response?.status === 401) {
        setError('Session expired. Please log in again.');
      } else if (error.type === 'network_error') {
        setError('Network error. Please check your connection.');
      } else {
        setError('Failed to load file details. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFileDetails(null);
    setError('');
    setShowDeleteConfirm(false);
    onClose();
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
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
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

  const handleDownload = async () => {
    try {
      console.log(`Downloading file ID: ${fileId}`);
      const response = await fileAPI.downloadFile(fileId);
      
      // Create blob and download
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileDetails.original_filename;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch (error) {
      console.error('Download failed:', error);
      // You could add a toast notification here
    }
  };

  const handleCopyHash = async (hash) => {
    try {
      await navigator.clipboard.writeText(hash);
      // You could add a toast notification here for success
      console.log('Hash copied to clipboard');
    } catch (error) {
      console.error('Failed to copy hash:', error);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = hash;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  };

  const truncateHash = (hash) => {
    if (!hash) return 'N/A';
    return hash.length > 16 ? `${hash.substring(0, 16)}...` : hash;
  };

  const handleDeleteFile = async () => {
    setIsDeleting(true);
    setError('');

    try {
      console.log(`Deleting file ID: ${fileId}`);
      await fileAPI.deleteFile(fileId);
      console.log('File deleted successfully');
      
      // Notify parent component about deletion
      if (onFileDeleted) {
        onFileDeleted(fileId);
      }
      
      // Close modal
      handleClose();
    } catch (error) {
      console.error('Failed to delete file:', error);
      
      if (error.response?.status === 404) {
        setError('File not found or already deleted.');
      } else if (error.response?.status === 401) {
        setError('Session expired. Please log in again.');
      } else if (error.response?.status === 403) {
        setError('You do not have permission to delete this file.');
      } else if (error.type === 'network_error') {
        setError('Network error. Please check your connection.');
      } else {
        setError('Failed to delete file. Please try again.');
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const confirmDelete = () => {
    setShowDeleteConfirm(true);
  };

  const cancelDelete = () => {
    setShowDeleteConfirm(false);
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '16px',
        padding: '32px',
        width: '100%',
        maxWidth: '600px',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <h2 style={{
            fontSize: '24px',
            fontWeight: '700',
            color: '#1f2937',
            margin: 0
          }}>
            File Details
          </h2>
          <button
            onClick={handleClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              color: '#6b7280',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px'
            }}
          >
            ×
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 16px' }}></div>
            <p style={{ color: '#6b7280', fontSize: '14px' }}>Loading file details...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px',
            color: '#dc2626',
            fontSize: '14px',
            textAlign: 'center'
          }}>
            {error}
            <button
              onClick={fetchFileDetails}
              style={{
                marginLeft: '12px',
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

        {/* File Details */}
        {fileDetails && (
          <>
            {/* File Icon and Name */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              marginBottom: '24px',
              padding: '16px',
              backgroundColor: '#f9fafb',
              borderRadius: '8px',
              border: '1px solid #e5e7eb'
            }}>
              <div style={{ fontSize: '48px' }}>
                {getMimeTypeIcon(fileDetails.mime_type)}
              </div>
              <div style={{ flex: 1 }}>
                <h3 style={{
                  fontSize: '18px',
                  fontWeight: '600',
                  color: '#1f2937',
                  margin: '0 0 4px 0',
                  wordBreak: 'break-word'
                }}>
                  {fileDetails.original_filename}
                </h3>
                <p style={{
                  fontSize: '14px',
                  color: '#6b7280',
                  margin: 0
                }}>
                  {formatBytes(fileDetails.size)} • {fileDetails.mime_type || 'Unknown type'}
                </p>
              </div>
              <button
                onClick={handleDownload}
                style={{
                  padding: '8px 16px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                📥 Download
              </button>
            </div>

            {/* File Information Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '16px',
              marginBottom: '24px'
            }}>
              <div style={{
                padding: '16px',
                backgroundColor: '#f0f9ff',
                borderRadius: '8px',
                border: '1px solid #bae6fd'
              }}>
                <h4 style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#0c4a6e',
                  margin: '0 0 8px 0'
                }}>
                  📅 Upload Information
                </h4>
                <div style={{ fontSize: '13px', color: '#374151', lineHeight: '1.5' }}>
                  <strong>Uploaded:</strong> {formatDate(fileDetails.uploaded_at)}
                </div>
              </div>

              <div style={{
                padding: '16px',
                backgroundColor: '#f0fdf4',
                borderRadius: '8px',
                border: '1px solid #86efac'
              }}>
                <h4 style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#15803d',
                  margin: '0 0 8px 0'
                }}>
                  🔧 Technical Details
                </h4>
                <div style={{ fontSize: '13px', color: '#374151', lineHeight: '1.5' }}>
                  <strong>MIME Type:</strong> {fileDetails.mime_type || 'Unknown'}<br/>
                  <strong>File Hash:</strong> 
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px', 
                    marginTop: '4px' 
                  }}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '11px',
                      backgroundColor: '#f3f4f6',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      border: '1px solid #e5e7eb'
                    }}>
                      {truncateHash(fileDetails.file_hash)}
                    </span>
                    {fileDetails.file_hash && (
                      <button
                        onClick={() => handleCopyHash(fileDetails.file_hash)}
                        style={{
                          padding: '4px 6px',
                          background: '#059669',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '10px',
                          cursor: 'pointer',
                          fontWeight: '500'
                        }}
                        title="Copy full hash to clipboard"
                      >
                        📋 Copy
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Tags Section */}
            <div style={{
              padding: '16px',
              backgroundColor: '#fefbef',
              borderRadius: '8px',
              border: '1px solid #fde047',
              marginBottom: '16px'
            }}>
              <h4 style={{
                fontSize: '14px',
                fontWeight: '600',
                color: '#a16207',
                margin: '0 0 8px 0'
              }}>
                🏷️ Tags
              </h4>
              {fileDetails.tags && fileDetails.tags.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {fileDetails.tags.map((tag, index) => (
                    <span
                      key={index}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#e0e7ff',
                        color: '#3730a3',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '500'
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: '13px', color: '#6b7280', margin: 0, fontStyle: 'italic' }}>
                  No tags assigned to this file
                </p>
              )}
            </div>

            {/* Delete Confirmation */}
            {showDeleteConfirm && (
              <div style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '16px'
              }}>
                <h4 style={{
                  fontSize: '16px',
                  fontWeight: '600',
                  color: '#dc2626',
                  margin: '0 0 8px 0'
                }}>
                  ⚠️ Confirm File Deletion
                </h4>
                <p style={{
                  fontSize: '14px',
                  color: '#7f1d1d',
                  margin: '0 0 16px 0',
                  lineHeight: '1.5'
                }}>
                  Are you sure you want to delete "<strong>{fileDetails?.original_filename}</strong>"? 
                  This action cannot be undone.
                </p>
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  justifyContent: 'flex-end'
                }}>
                  <button
                    onClick={cancelDelete}
                    disabled={isDeleting}
                    style={{
                      padding: '6px 12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px',
                      background: 'white',
                      color: '#374151',
                      fontSize: '12px',
                      cursor: isDeleting ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDeleteFile}
                    disabled={isDeleting}
                    style={{
                      padding: '6px 12px',
                      border: 'none',
                      borderRadius: '4px',
                      background: isDeleting ? '#fca5a5' : '#dc2626',
                      color: 'white',
                      fontSize: '12px',
                      cursor: isDeleting ? 'not-allowed' : 'pointer',
                      fontWeight: '500'
                    }}
                  >
                    {isDeleting ? '🗑️ Deleting...' : '🗑️ Delete File'}
                  </button>
                </div>
              </div>
            )}

            {/* Actions */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '12px',
              paddingTop: '16px',
              borderTop: '1px solid #e5e7eb'
            }}>
              <button
                onClick={confirmDelete}
                disabled={isDeleting || isLoading || !fileDetails}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '6px',
                  background: (isDeleting || isLoading || !fileDetails) ? '#fca5a5' : '#dc2626',
                  color: 'white',
                  fontSize: '14px',
                  cursor: (isDeleting || isLoading || !fileDetails) ? 'not-allowed' : 'pointer',
                  fontWeight: '500'
                }}
              >
                {isDeleting ? '🗑️ Deleting...' : '🗑️ Delete'}
              </button>
              
              <button
                onClick={handleClose}
                disabled={isDeleting}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  background: 'white',
                  color: '#374151',
                  fontSize: '14px',
                  cursor: isDeleting ? 'not-allowed' : 'pointer'
                }}
              >
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default FileDetailsModal; 