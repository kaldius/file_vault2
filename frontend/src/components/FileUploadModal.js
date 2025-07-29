import React, { useState } from 'react';
import { fileAPI } from '../services/api';

const FileUploadModal = ({ isOpen, onClose, onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [tags, setTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const resetModal = () => {
    setSelectedFile(null);
    setTags('');
    setUploadError('');
    setIsUploading(false);
    setDragActive(false);
  };

  const handleClose = () => {
    if (!isUploading) {
      resetModal();
      onClose();
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadError('');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setUploadError('');
    }
  };

  const parseTagsInput = (tagsString) => {
    if (!tagsString.trim()) return [];
    return tagsString
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)
      .slice(0, 10); // Limit to 10 tags
  };

  const validateFile = (file) => {
    const maxSize = 100 * 1024 * 1024; // 100MB
    
    if (file.size > maxSize) {
      return 'File size must be less than 100MB';
    }
    
    return null;
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setUploadError('Please select a file to upload');
      return;
    }

    const validationError = validateFile(selectedFile);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setIsUploading(true);
    setUploadError('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const parsedTags = parseTagsInput(tags);
      if (parsedTags.length > 0) {
        formData.append('tags', JSON.stringify(parsedTags));
      }

      console.log('Uploading file:', selectedFile.name, 'with tags:', parsedTags);
      
      const response = await fileAPI.uploadFile(formData);
      console.log('Upload successful:', response.data);
      
      // Call success callback
      if (onUploadSuccess) {
        onUploadSuccess(response.data);
      }
      
      // Reset and close modal
      resetModal();
      onClose();
      
    } catch (error) {
      console.error('Upload failed:', error);
      
      if (error.response?.data) {
        const errorData = error.response.data;
        if (typeof errorData === 'object') {
          // Handle field-specific errors
          const errorMessages = [];
          if (errorData.file) errorMessages.push(`File: ${errorData.file}`);
          if (errorData.tags) errorMessages.push(`Tags: ${errorData.tags}`);
          if (errorData.non_field_errors) errorMessages.push(errorData.non_field_errors);
          
          setUploadError(errorMessages.join(', ') || 'Upload failed');
        } else {
          setUploadError(errorData || 'Upload failed');
        }
      } else if (error.type === 'network_error') {
        setUploadError('Network error. Please check your connection.');
      } else {
        setUploadError('Upload failed. Please try again.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
        maxWidth: '500px',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      }}>
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
            Upload File
          </h2>
          <button
            onClick={handleClose}
            disabled={isUploading}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              color: '#6b7280',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              padding: '4px',
              borderRadius: '4px'
            }}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleUpload}>
          {/* File Upload Area */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px'
            }}>
              Select File
            </label>
            
            <div
              style={{
                border: `2px dashed ${dragActive ? '#667eea' : '#d1d5db'}`,
                borderRadius: '8px',
                padding: '24px',
                textAlign: 'center',
                backgroundColor: dragActive ? '#f0f4ff' : '#f9fafb',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => !isUploading && document.getElementById('file-input').click()}
            >
              <input
                id="file-input"
                type="file"
                onChange={handleFileSelect}
                disabled={isUploading}
                style={{ display: 'none' }}
              />
              
              {selectedFile ? (
                <div>
                  <div style={{ fontSize: '24px', marginBottom: '8px' }}>📄</div>
                  <div style={{ fontWeight: '500', color: '#374151', marginBottom: '4px' }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: '14px', color: '#6b7280' }}>
                    {formatFileSize(selectedFile.size)}
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    disabled={isUploading}
                    style={{
                      marginTop: '8px',
                      padding: '4px 8px',
                      background: '#ef4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '12px',
                      cursor: isUploading ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '48px', marginBottom: '16px' }}>📁</div>
                  <p style={{ color: '#374151', marginBottom: '8px' }}>
                    Drop your file here or click to browse
                  </p>
                  <p style={{ fontSize: '14px', color: '#6b7280' }}>
                    Maximum file size: 100MB
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Tags Input */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px'
            }}>
              Tags (optional)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              disabled={isUploading}
              placeholder="document, important, work (comma-separated)"
              style={{
                width: '100%',
                padding: '12px 16px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                fontSize: '14px',
                backgroundColor: isUploading ? '#f3f4f6' : '#f9fafb'
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              Separate multiple tags with commas (max 10 tags)
            </p>
          </div>

          {/* Error Message */}
          {uploadError && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '24px',
              color: '#dc2626',
              fontSize: '14px'
            }}>
              {uploadError}
            </div>
          )}

          {/* Action Buttons */}
          <div style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'flex-end'
          }}>
            <button
              type="button"
              onClick={handleClose}
              disabled={isUploading}
              style={{
                padding: '12px 24px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                background: 'white',
                color: '#374151',
                fontSize: '14px',
                fontWeight: '500',
                cursor: isUploading ? 'not-allowed' : 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              style={{
                padding: '12px 24px',
                border: 'none',
                borderRadius: '8px',
                background: (!selectedFile || isUploading) ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                fontSize: '14px',
                fontWeight: '500',
                cursor: (!selectedFile || isUploading) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isUploading && (
                <div className="loading-spinner" style={{ width: '16px', height: '16px' }}></div>
              )}
              {isUploading ? 'Uploading...' : 'Upload File'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FileUploadModal; 