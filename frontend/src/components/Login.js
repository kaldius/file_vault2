import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authAPI } from '../services/api';
import { setAuthTokens, setUser } from '../utils/auth';

const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (errors[name] || errors.general) {
      setErrors(prev => ({
        ...prev,
        [name]: '',
        general: '' // Clear general error when user starts typing
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const response = await authAPI.login({
        username: formData.username,
        password: formData.password,
      });

      const { user, access, refresh } = response.data;
      
      // Store tokens and user data
      setAuthTokens(access, refresh);
      setUser(user);
      
      // Call parent callback
      onLogin(user);
      
    } catch (error) {
      if (error.response?.data) {
        const serverErrors = error.response.data;
        if (typeof serverErrors === 'object') {
          // Handle Django REST Framework validation errors
          const newErrors = {};
          
          // Check for non_field_errors (general authentication errors)
          if (serverErrors.non_field_errors) {
            newErrors.general = Array.isArray(serverErrors.non_field_errors) 
              ? serverErrors.non_field_errors[0] 
              : serverErrors.non_field_errors;
          }
          
          // Handle field-specific errors
          if (serverErrors.username) {
            newErrors.username = Array.isArray(serverErrors.username)
              ? serverErrors.username[0]
              : serverErrors.username;
          }
          
          if (serverErrors.password) {
            newErrors.password = Array.isArray(serverErrors.password)
              ? serverErrors.password[0] 
              : serverErrors.password;
          }
          
          // If no specific errors were found, set a general error
          if (Object.keys(newErrors).length === 0) {
            newErrors.general = 'Invalid username or password';
          }
          
          setErrors(newErrors);
        } else {
          setErrors({ general: 'Invalid username or password' });
        }
      } else {
        setErrors({ general: 'Network error. Please try again.' });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-title">Welcome Back</h1>
          <p className="auth-subtitle">Sign in to your File Vault account</p>
        </div>

        <form onSubmit={handleSubmit}>
          {errors.general && (
            <div className="error-message" style={{ 
              marginBottom: '16px', 
              textAlign: 'center',
              padding: '12px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              {errors.general}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="username" className="form-label">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className={`form-input ${errors.username ? 'error' : ''}`}
              placeholder="Enter your username"
            />
            {errors.username && (
              <div className="error-message">{errors.username}</div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className={`form-input ${errors.password ? 'error' : ''}`}
              placeholder="Enter your password"
            />
            {errors.password && (
              <div className="error-message">{errors.password}</div>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
          >
            {loading && <div className="loading-spinner"></div>}
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-links">
          <p>
            Don't have an account?{' '}
            <Link to="/register" className="auth-link">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login; 