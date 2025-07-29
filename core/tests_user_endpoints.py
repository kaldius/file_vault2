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


class UserProfileAPITests(APITestCase):
    """
    Test suite for /api/users/me/ endpoint
    """
    
    def setUp(self):
        """Set up test data"""
        self.user_profile_url = reverse('user_profile')
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            storage_quota=2147483648,  # 2GB
            storage_used=1073741824    # 1GB
        )
        
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.test_user)
        self.access_token = str(refresh.access_token)
        
    def test_user_profile_success(self):
        """Test successful retrieval of user profile"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.user_profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response structure and data
        expected_data = {
            'id': self.test_user.id,
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'storage_quota': 2147483648,
            'storage_used': 1073741824
        }
        
        response_data = response.data
        # Check that created_at is present and has correct format
        self.assertIn('created_at', response_data)
        self.assertIsInstance(response_data['created_at'], str)
        
        # Remove created_at for comparison since it's dynamic
        response_data.pop('created_at')
        
        self.assertEqual(response_data, expected_data)
        
    def test_user_profile_unauthenticated(self):
        """Test user profile endpoint without authentication"""
        response = self.client.get(self.user_profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_user_profile_invalid_token(self):
        """Test user profile endpoint with invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.get(self.user_profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_user_profile_different_user_data(self):
        """Test that each user gets their own profile data"""
        # Create second user
        second_user = User.objects.create_user(
            username='seconduser',
            email='second@example.com',
            password='testpassword123',
            first_name='Second',
            last_name='User',
            storage_quota=5368709120,  # 5GB
            storage_used=2147483648    # 2GB
        )
        
        # Get token for second user
        refresh = RefreshToken.for_user(second_user)
        second_access_token = str(refresh.access_token)
        
        # Test first user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response1 = self.client.get(self.user_profile_url)
        
        # Test second user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {second_access_token}')
        response2 = self.client.get(self.user_profile_url)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify different user data
        self.assertEqual(response1.data['username'], 'testuser')
        self.assertEqual(response2.data['username'], 'seconduser')
        self.assertEqual(response1.data['storage_quota'], 2147483648)
        self.assertEqual(response2.data['storage_quota'], 5368709120)




 