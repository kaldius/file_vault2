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


class FileStatsAPITests(APITestCase):
    """
    Test suite for /api/files/stats/ endpoint
    """
    
    def setUp(self):
        """Set up test data"""
        self.file_stats_url = reverse('file_stats')
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            storage_quota=2147483648,  # 2GB
            storage_used=0
        )
        
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.test_user)
        self.access_token = str(refresh.access_token)
        
    def test_file_stats_empty_user(self):
        """Test file stats for user with no files"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_data = {
            'total_files': 0,
            'total_size': 0,
            'storage_used': 0,
            'storage_quota': 2147483648,
            'storage_percentage': 0.0
        }
        
        self.assertEqual(response.data, expected_data)
        
    def test_file_stats_with_files(self):
        """Test file stats for user with uploaded files"""
        # Create test files and user file associations
        file1 = File.objects.create(
            hash='hash1',
            size=1024000,  # ~1MB
            storage_path='test/path1',
            mime_type='text/plain'
        )
        
        file2 = File.objects.create(
            hash='hash2',
            size=2048000,  # ~2MB
            storage_path='test/path2',
            mime_type='application/pdf'
        )
        
        # Create user file associations
        UserFile.objects.create(
            user=self.test_user,
            file=file1,
            original_filename='test1.txt',
            tags=['document']
        )
        
        UserFile.objects.create(
            user=self.test_user,
            file=file2,
            original_filename='test2.pdf',
            tags=['pdf', 'important']
        )
        
        # Update user storage_used
        self.test_user.storage_used = 3072000  # 3MB total
        self.test_user.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        expected_data = {
            'total_files': 2,
            'total_size': 3072000,  # Sum of file sizes
            'storage_used': 3072000,
            'storage_quota': 2147483648,
            'storage_percentage': round((3072000 / 2147483648) * 100, 2)
        }
        
        self.assertEqual(response.data, expected_data)
        
    def test_file_stats_with_deleted_files(self):
        """Test file stats ignores soft-deleted files"""
        # Create test file
        file1 = File.objects.create(
            hash='hash1',
            size=1024000,
            storage_path='test/path1',
            mime_type='text/plain'
        )
        
        # Create active user file
        UserFile.objects.create(
            user=self.test_user,
            file=file1,
            original_filename='active.txt',
            tags=['active']
        )
        
        # Create deleted user file
        UserFile.objects.create(
            user=self.test_user,
            file=file1,
            original_filename='deleted.txt',
            tags=['deleted'],
            deleted=True
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only count the active file
        expected_data = {
            'total_files': 1,
            'total_size': 1024000,
            'storage_used': 0,  # User storage_used hasn't been updated
            'storage_quota': 2147483648,
            'storage_percentage': 0.0
        }
        
        self.assertEqual(response.data, expected_data)
        
    def test_file_stats_unauthenticated(self):
        """Test file stats endpoint without authentication"""
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_file_stats_different_users(self):
        """Test that file stats are isolated per user"""
        # Create second user
        second_user = User.objects.create_user(
            username='seconduser',
            email='second@example.com',
            password='testpassword123',
            storage_quota=1073741824,  # 1GB
            storage_used=0
        )
        
        # Create file for first user
        file1 = File.objects.create(
            hash='hash1',
            size=1024000,
            storage_path='test/path1',
            mime_type='text/plain'
        )
        
        UserFile.objects.create(
            user=self.test_user,
            file=file1,
            original_filename='user1_file.txt',
            tags=['user1']
        )
        
        # Create file for second user  
        file2 = File.objects.create(
            hash='hash2',
            size=2048000,
            storage_path='test/path2',
            mime_type='application/pdf'
        )
        
        UserFile.objects.create(
            user=second_user,
            file=file2,
            original_filename='user2_file.pdf',
            tags=['user2']
        )
        
        # Get tokens for both users
        refresh2 = RefreshToken.for_user(second_user)
        second_access_token = str(refresh2.access_token)
        
        # Test first user stats
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response1 = self.client.get(self.file_stats_url)
        
        # Test second user stats
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {second_access_token}')
        response2 = self.client.get(self.file_stats_url)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify isolated stats
        self.assertEqual(response1.data['total_files'], 1)
        self.assertEqual(response1.data['total_size'], 1024000)
        self.assertEqual(response2.data['total_files'], 1)
        self.assertEqual(response2.data['total_size'], 2048000)
        
    def test_file_stats_storage_percentage_calculation(self):
        """Test storage percentage calculation accuracy"""
        # Set specific quota and usage for precise calculation
        self.test_user.storage_quota = 10000000  # 10MB
        self.test_user.storage_used = 2500000    # 2.5MB
        self.test_user.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2.5MB / 10MB = 25%
        expected_percentage = 25.0
        self.assertEqual(response.data['storage_percentage'], expected_percentage)
        
    def test_file_stats_zero_quota_handling(self):
        """Test file stats when user has zero quota"""
        self.test_user.storage_quota = 0
        self.test_user.storage_used = 0
        self.test_user.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.file_stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should handle division by zero gracefully
        self.assertEqual(response.data['storage_percentage'], 0.0)


class UserEndpointsIntegrationTests(APITestCase):
    """
    Integration tests for user-related endpoints
    """
    
    def setUp(self):
        """Set up test data"""
        self.user_profile_url = reverse('user_profile')
        self.file_stats_url = reverse('file_stats')
        self.file_upload_url = reverse('file_upload')
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            storage_quota=10485760,  # 10MB
            storage_used=0
        )
        
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.test_user)
        self.access_token = str(refresh.access_token)
        
    def test_user_profile_and_stats_consistency(self):
        """Test that user profile and file stats return consistent storage data"""
        # Update user storage
        self.test_user.storage_used = 5242880  # 5MB
        self.test_user.save()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Get user profile
        profile_response = self.client.get(self.user_profile_url)
        
        # Get file stats
        stats_response = self.client.get(self.file_stats_url)
        
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        
        # Verify storage data consistency
        self.assertEqual(
            profile_response.data['storage_used'],
            stats_response.data['storage_used']
        )
        self.assertEqual(
            profile_response.data['storage_quota'],
            stats_response.data['storage_quota']
        ) 