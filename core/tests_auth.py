from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
import json
import hashlib
import tempfile
import os
from .models import File, UserFile

User = get_user_model()

class AuthenticationAPITests(APITestCase):
    """
    Comprehensive test suite for authentication endpoints:
    - POST /api/auth/register/
    - POST /api/auth/login/
    - POST /api/auth/logout/
    - POST /api/auth/token/refresh/
    """
    
    def setUp(self):
        """Set up test data"""
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.refresh_url = reverse('token_refresh')
        
        self.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        self.login_data = {
            'username': 'testuser',
            'password': 'securepassword123'
        }

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.valid_user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Check user data structure
        user_data = response.data['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')
        self.assertEqual(user_data['first_name'], 'Test')
        self.assertEqual(user_data['last_name'], 'User')
        self.assertIn('id', user_data)
        
        # Verify user was created in database
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password_confirm'] = 'differentpassword'
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_registration_weak_password(self):
        """Test registration with weak password"""
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = '123'
        invalid_data['password_confirm'] = '123'
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_registration_duplicate_username(self):
        """Test registration with duplicate username"""
        # Create first user
        self.client.post(self.register_url, self.valid_user_data, format='json')
        
        # Try to create another user with same username
        duplicate_data = self.valid_user_data.copy()
        duplicate_data['email'] = 'different@example.com'
        
        response = self.client.post(self.register_url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # Create first user
        self.client.post(self.register_url, self.valid_user_data, format='json')
        
        # Try to create another user with same email
        duplicate_data = self.valid_user_data.copy()
        duplicate_data['username'] = 'differentuser'
        
        response = self.client.post(self.register_url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_user_registration_missing_fields(self):
        """Test registration with missing required fields"""
        incomplete_data = {
            'username': 'testuser',
            'password': 'securepassword123'
            # Missing email, password_confirm, etc.
        }
        
        response = self.client.post(self.register_url, incomplete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password_confirm', response.data)

    def test_user_login_success(self):
        """Test successful user login"""
        # First register a user
        self.client.post(self.register_url, self.valid_user_data, format='json')
        
        # Then login
        response = self.client.post(self.login_url, self.login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Check user data structure
        user_data = response.data['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        # First register a user
        self.client.post(self.register_url, self.valid_user_data, format='json')
        
        # Try login with wrong password
        invalid_login_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, invalid_login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_login_nonexistent_user(self):
        """Test login with non-existent user"""
        nonexistent_login_data = {
            'username': 'nonexistent',
            'password': 'somepassword'
        }
        
        response = self.client.post(self.login_url, nonexistent_login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_login_missing_fields(self):
        """Test login with missing fields"""
        incomplete_login_data = {
            'username': 'testuser'
            # Missing password
        }
        
        response = self.client.post(self.login_url, incomplete_login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_user_login_inactive_user(self):
        """Test login with inactive user"""
        # Register and then deactivate user
        self.client.post(self.register_url, self.valid_user_data, format='json')
        user = User.objects.get(username='testuser')
        user.is_active = False
        user.save()
        
        response = self.client.post(self.login_url, self.login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_user_logout_success(self):
        """Test successful user logout"""
        # Register and login to get tokens
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        refresh_token = register_response.data['refresh']
        access_token = register_response.data['access']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Logout
        logout_data = {'refresh': refresh_token}
        response = self.client.post(self.logout_url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertIsNone(response.data)

    def test_user_logout_invalid_token(self):
        """Test logout with invalid refresh token"""
        # Register and login to get access token
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        access_token = register_response.data['access']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Try logout with invalid refresh token
        logout_data = {'refresh': 'invalid_token'}
        response = self.client.post(self.logout_url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid', str(response.data[0]))

    def test_user_logout_missing_refresh_token(self):
        """Test logout without refresh token"""
        # Register and login to get access token
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        access_token = register_response.data['access']
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Try logout without refresh token
        response = self.client.post(self.logout_url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)

    def test_user_logout_unauthenticated(self):
        """Test logout without authentication"""
        logout_data = {'refresh': 'some_token'}
        response = self.client.post(self.logout_url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Test successful token refresh"""
        # Register to get tokens
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        refresh_token = register_response.data['refresh']
        
        # Refresh token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # With rotation enabled, should also get new refresh token
        self.assertIn('refresh', response.data)

    def test_token_refresh_invalid_token(self):
        """Test token refresh with invalid refresh token"""
        refresh_data = {'refresh': 'invalid_token'}
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_missing_token(self):
        """Test token refresh without refresh token"""
        response = self.client.post(self.refresh_url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)

    def test_token_refresh_blacklisted_token(self):
        """Test token refresh with blacklisted token"""
        # Register and login to get tokens
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        refresh_token = register_response.data['refresh']
        access_token = register_response.data['access']
        
        # First, logout to blacklist the token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_data = {'refresh': refresh_token}
        self.client.post(self.logout_url, logout_data, format='json')
        
        # Try to refresh with blacklisted token
        refresh_data = {'refresh': refresh_token}
        response = self.client.post(self.refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_complete_auth_flow(self):
        """Test complete authentication flow: register -> login -> logout -> refresh (should fail)"""
        # 1. Register
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # 2. Login
        login_response = self.client.post(self.login_url, self.login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        refresh_token = login_response.data['refresh']
        access_token = login_response.data['access']
        
        # 3. Use access token for authenticated request (logout)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_data = {'refresh': refresh_token}
        logout_response = self.client.post(self.logout_url, logout_data, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)
        
        # 4. Try to refresh with blacklisted token (should fail)
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post(self.refresh_url, refresh_data, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_authentication(self):
        """Test that access tokens work for authenticated endpoints"""
        # Register to get tokens
        register_response = self.client.post(self.register_url, self.valid_user_data, format='json')
        access_token = register_response.data['access']
        
        # Use access token to access logout endpoint (just to test auth, don't actually logout)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # This should return 400 (missing refresh token) not 401 (unauthorized)
        # which proves the access token authentication is working
        response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', response.data)

    def test_invalid_access_token_authentication(self):
        """Test that invalid access tokens are rejected"""
        # Try to access logout endpoint with invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        response = self.client.post(self.logout_url, {'refresh': 'some_token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_access_token_authentication(self):
        """Test that missing access tokens are rejected"""
        # Try to access logout endpoint without token
        response = self.client.post(self.logout_url, {'refresh': 'some_token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
