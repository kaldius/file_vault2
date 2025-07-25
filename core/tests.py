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


class FileUploadAPITests(APITestCase):
    """
    Comprehensive test suite for file upload endpoint:
    - POST /api/files/upload/
    """
    
    def setUp(self):
        """Set up test data"""
        self.upload_url = reverse('file_upload')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Get access token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Create test file content
        self.test_file_content = b"This is a test file content for upload testing."
        self.test_file_hash = hashlib.sha256(self.test_file_content).hexdigest()
        
        # Create test files
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_file_content,
            content_type="text/plain"
        )
        
        self.test_pdf = SimpleUploadedFile(
            "document.pdf",
            b"%PDF-1.4 fake pdf content",
            content_type="application/pdf"
        )

    def test_file_upload_success(self):
        """Test successful file upload"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {
            'file': self.test_file,
            'tags': json.dumps(['test', 'document'])
        }
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response structure
        response_data = response.data
        self.assertIn('id', response_data)
        self.assertEqual(response_data['original_filename'], 'test.txt')
        self.assertEqual(response_data['tags'], ['test', 'document'])
        self.assertEqual(response_data['size'], len(self.test_file_content))
        self.assertEqual(response_data['mime_type'], 'text/plain')
        self.assertEqual(response_data['file_hash'], self.test_file_hash)
        self.assertIn('uploaded_at', response_data)
        
        # Verify database objects were created
        self.assertTrue(File.objects.filter(hash=self.test_file_hash).exists())
        self.assertTrue(UserFile.objects.filter(user=self.user, original_filename='test.txt').exists())

    def test_file_upload_without_tags(self):
        """Test file upload without tags"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {'file': self.test_file}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tags'], [])

    def test_file_upload_duplicate_deduplication(self):
        """Test file deduplication for identical content"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Upload first file
        data1 = {
            'file': SimpleUploadedFile("file1.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['first'])
        }
        response1 = self.client.post(self.upload_url, data1, format='multipart')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Upload second file with same content but different name
        data2 = {
            'file': SimpleUploadedFile("file2.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['second'])
        }
        response2 = self.client.post(self.upload_url, data2, format='multipart')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify both files reference the same File object (deduplication)
        file1_id = response1.data['id']
        file2_id = response2.data['id']
        
        user_file1 = UserFile.objects.get(id=file1_id)
        user_file2 = UserFile.objects.get(id=file2_id)
        
        self.assertEqual(user_file1.file.hash, user_file2.file.hash)
        self.assertEqual(user_file1.file.id, user_file2.file.id)
        
        # Verify only one File object exists
        self.assertEqual(File.objects.filter(hash=self.test_file_hash).count(), 1)

    def test_file_upload_duplicate_same_name_fails(self):
        """Test that uploading same file with same name by same user fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Upload first file
        data = {
            'file': SimpleUploadedFile("test.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['test'])
        }
        response1 = self.client.post(self.upload_url, data, format='multipart')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to upload same file with same name again
        data = {
            'file': SimpleUploadedFile("test.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['test2'])
        }
        response2 = self.client.post(self.upload_url, data, format='multipart')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response2.data)

    def test_file_upload_unauthenticated(self):
        """Test file upload without authentication"""
        data = {'file': self.test_file}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_file_upload_missing_file(self):
        """Test file upload without file parameter"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {'tags': json.dumps(['test'])}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_file_upload_oversized_file(self):
        """Test file upload with file exceeding size limit"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create a file larger than 100MB limit
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        large_file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
        
        data = {'file': large_file}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_file_upload_invalid_tags_format(self):
        """Test file upload with invalid tags format"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {
            'file': self.test_file,
            'tags': 'not json'  # Invalid JSON
        }
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_file_upload_tags_not_array(self):
        """Test file upload with tags not being an array"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {
            'file': self.test_file,
            'tags': json.dumps("not an array")
        }
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_file_upload_tag_too_long(self):
        """Test file upload with tag exceeding length limit"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        long_tag = "x" * 51  # Exceeds 50 character limit
        data = {
            'file': self.test_file,
            'tags': json.dumps([long_tag])
        }
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_file_upload_non_string_tags(self):
        """Test file upload with non-string tags"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {
            'file': self.test_file,
            'tags': json.dumps(['valid', 123, 'also_valid'])  # Number in tags
        }
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', response.data)

    def test_file_upload_storage_usage_update(self):
        """Test that user storage usage is updated after file upload"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        initial_storage = self.user.storage_used
        
        data = {'file': self.test_file}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Refresh user from database
        self.user.refresh_from_db()
        
        expected_storage = initial_storage + len(self.test_file_content)
        self.assertEqual(self.user.storage_used, expected_storage)

    def test_file_upload_different_users_same_file(self):
        """Test that different users can upload the same file content"""
        # Create second user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        refresh2 = RefreshToken.for_user(user2)
        access_token2 = str(refresh2.access_token)
        
        # First user uploads file
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        data1 = {
            'file': SimpleUploadedFile("file.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['user1'])
        }
        response1 = self.client.post(self.upload_url, data1, format='multipart')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second user uploads same content with same filename
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token2}')
        data2 = {
            'file': SimpleUploadedFile("file.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['user2'])
        }
        response2 = self.client.post(self.upload_url, data2, format='multipart')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify both uploads succeeded but reference same File object
        user_file1 = UserFile.objects.get(user=self.user, original_filename='file.txt')
        user_file2 = UserFile.objects.get(user=user2, original_filename='file.txt')
        
        self.assertEqual(user_file1.file.hash, user_file2.file.hash)
        self.assertEqual(user_file1.file.id, user_file2.file.id)
        self.assertEqual(user_file1.tags, ['user1'])
        self.assertEqual(user_file2.tags, ['user2'])

    def test_file_upload_mime_type_detection(self):
        """Test that MIME types are correctly detected and stored"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Test PDF file
        data = {'file': self.test_pdf}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['mime_type'], 'application/pdf')

    def test_file_upload_hash_calculation(self):
        """Test that SHA-256 hash is correctly calculated"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        data = {'file': self.test_file}
        
        response = self.client.post(self.upload_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        expected_hash = hashlib.sha256(self.test_file_content).hexdigest()
        self.assertEqual(response.data['file_hash'], expected_hash)
        
        # Verify in database
        file_obj = File.objects.get(hash=expected_hash)
        self.assertEqual(file_obj.hash, expected_hash)


class FileListAPITests(APITestCase):
    """
    Comprehensive test suite for file listing endpoint:
    - GET /api/files/
    """
    
    def setUp(self):
        """Set up test data"""
        self.list_url = reverse('file_list')
        self.upload_url = reverse('file_upload')
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Get access tokens
        refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(refresh1.access_token)
        
        refresh2 = RefreshToken.for_user(self.user2)
        self.access_token2 = str(refresh2.access_token)
        
        # Create test files for user1
        self.setup_test_files()

    def setup_test_files(self):
        """Create test files for testing"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Upload various test files
        test_files = [
            {
                'filename': 'document.pdf',
                'content': b'%PDF-1.4 fake pdf content',
                'content_type': 'application/pdf',
                'tags': ['work', 'important']
            },
            {
                'filename': 'image.jpg',
                'content': b'fake jpeg content',
                'content_type': 'image/jpeg',
                'tags': ['photo', 'vacation']
            },
            {
                'filename': 'text.txt',
                'content': b'simple text file content',
                'content_type': 'text/plain',
                'tags': ['note']
            }
        ]
        
        self.uploaded_files = []
        for file_data in test_files:
            uploaded_file = SimpleUploadedFile(
                file_data['filename'],
                file_data['content'],
                content_type=file_data['content_type']
            )
            
            data = {
                'file': uploaded_file,
                'tags': json.dumps(file_data['tags'])
            }
            
            response = self.client.post(self.upload_url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.uploaded_files.append(response.data)

    def test_file_list_success(self):
        """Test successful file listing"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 3)  # 3 test files uploaded
        
        # Check response structure
        first_file = response.data['results'][0]
        required_fields = ['id', 'original_filename', 'uploaded_at', 'tags', 'size', 'mime_type', 'file_hash']
        for field in required_fields:
            self.assertIn(field, first_file)

    def test_file_list_unauthenticated(self):
        """Test file listing without authentication"""
        # Create a fresh client instance to avoid authentication pollution
        from rest_framework.test import APIClient
        fresh_client = APIClient()
        
        response = fresh_client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_file_list_user_isolation(self):
        """Test that users only see their own files"""
        # User2 uploads a file
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token2}')
        uploaded_file = SimpleUploadedFile("user2_file.txt", b"user2 content", content_type="text/plain")
        data = {'file': uploaded_file}
        self.client.post(self.upload_url, data, format='multipart')
        
        # User2 should only see their own file
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'user2_file.txt')
        
        # User1 should see their 3 files
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_file_list_search_filename(self):
        """Test searching files by filename"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Search for 'document'
        response = self.client.get(self.list_url, {'search': 'document'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'document.pdf')

    def test_file_list_search_tags(self):
        """Test searching files by tags"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Search for 'work' tag
        response = self.client.get(self.list_url, {'search': 'work'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)  # document.pdf has 'work' tag

    def test_file_list_search_case_insensitive(self):
        """Test that search is case insensitive"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Search for 'DOCUMENT' (uppercase)
        response = self.client.get(self.list_url, {'search': 'DOCUMENT'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'document.pdf')

    def test_file_list_filter_by_tags(self):
        """Test filtering files by specific tag"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Filter by 'work' tag
        response = self.client.get(self.list_url, {'tags': 'work'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        
        for file_data in response.data['results']:
            self.assertIn('work', file_data['tags'])

    def test_file_list_filter_by_filename(self):
        """Test filtering files by filename"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Filter by filename containing 'text'
        response = self.client.get(self.list_url, {'filename': 'text'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'text.txt')

    def test_file_list_filter_by_mime_type(self):
        """Test filtering files by MIME type"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Filter by PDF MIME type
        response = self.client.get(self.list_url, {'mime_type': 'application/pdf'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'document.pdf')
        self.assertEqual(response.data['results'][0]['mime_type'], 'application/pdf')

    def test_file_list_filter_by_size_range(self):
        """Test filtering files by size range"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Filter files larger than 20 bytes (should get all files)
        response = self.client.get(self.list_url, {'size_min': '20'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)
        
        for file_data in response.data['results']:
            self.assertGreaterEqual(file_data['size'], 20)

    def test_file_list_filter_by_size_range_both(self):
        """Test filtering files by both min and max size"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Filter files between 15 and 30 bytes
        response = self.client.get(self.list_url, {'size_min': '15', 'size_max': '30'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        for file_data in response.data['results']:
            self.assertGreaterEqual(file_data['size'], 15)
            self.assertLessEqual(file_data['size'], 30)

    def test_file_list_filter_invalid_size_values(self):
        """Test filtering with invalid size values"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Invalid size values should be ignored
        response = self.client.get(self.list_url, {'size_min': 'invalid', 'size_max': 'also_invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)  # Should return all files

    def test_file_list_filter_by_upload_date(self):
        """Test filtering files by upload date"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Get a recent timestamp (files were just uploaded)
        from django.utils import timezone
        recent_time = timezone.now() - timezone.timedelta(minutes=1)
        
        # Filter files uploaded after 1 minute ago (should get all)
        response = self.client.get(self.list_url, {'uploaded_after': recent_time.isoformat()})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_file_list_filter_invalid_date_values(self):
        """Test filtering with invalid date values"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Invalid date values should be ignored
        response = self.client.get(self.list_url, {
            'uploaded_after': 'invalid_date',
            'uploaded_before': 'also_invalid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)  # Should return all files

    def test_file_list_ordering_by_filename(self):
        """Test ordering files by filename"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Order by filename ascending
        response = self.client.get(self.list_url, {'ordering': 'original_filename'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [file['original_filename'] for file in response.data['results']]
        self.assertEqual(filenames, sorted(filenames))
        
        # Order by filename descending
        response = self.client.get(self.list_url, {'ordering': '-original_filename'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        filenames = [file['original_filename'] for file in response.data['results']]
        self.assertEqual(filenames, sorted(filenames, reverse=True))

    def test_file_list_ordering_by_size(self):
        """Test ordering files by size"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Order by size ascending
        response = self.client.get(self.list_url, {'ordering': 'file__size'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sizes = [file['size'] for file in response.data['results']]
        self.assertEqual(sizes, sorted(sizes))

    def test_file_list_ordering_by_upload_date(self):
        """Test ordering files by upload date"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Order by upload date descending (default)
        response = self.client.get(self.list_url, {'ordering': '-uploaded_at'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dates = [file['uploaded_at'] for file in response.data['results']]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_file_list_ordering_invalid_field(self):
        """Test ordering with invalid field falls back to default"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Invalid ordering field should fall back to default (-uploaded_at)
        response = self.client.get(self.list_url, {'ordering': 'invalid_field'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dates = [file['uploaded_at'] for file in response.data['results']]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_file_list_pagination(self):
        """Test pagination functionality"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Test default pagination (20 items per page)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # With only 3 files, next should be None
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_file_list_pagination_custom_page_size(self):
        """Test custom page size"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Request page size of 2
        response = self.client.get(self.list_url, {'page_size': '2'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIsNotNone(response.data['next'])  # Should have next page

    def test_file_list_pagination_page_out_of_range(self):
        """Test requesting page out of range"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Request page 999 (way out of range)
        response = self.client.get(self.list_url, {'page': '999'})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_file_list_combined_filters(self):
        """Test combining multiple filters"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Search for 'work' and filter by application MIME type
        response = self.client.get(self.list_url, {
            'search': 'work',
            'mime_type': 'application/pdf'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['original_filename'], 'document.pdf')

    def test_file_list_no_files(self):
        """Test listing when user has no files"""
        # Create new user with no files
        user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123'
        )
        refresh3 = RefreshToken.for_user(user3)
        access_token3 = str(refresh3.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token3}')
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

    def test_file_list_excludes_deleted_files(self):
        """Test that soft-deleted files are not included in listing"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        # Get initial count
        response = self.client.get(self.list_url)
        initial_count = response.data['count']
        
        # Soft delete a file
        user_file = UserFile.objects.filter(user=self.user1).first()
        user_file.deleted = True
        user_file.save()
        
        # List should now have one less file
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], initial_count - 1)

    def test_file_list_response_format(self):
        """Test that response format matches documentation"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token1}')
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check pagination structure
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # Check file structure
        file_data = response.data['results'][0]
        required_fields = ['id', 'original_filename', 'uploaded_at', 'tags', 'size', 'mime_type', 'file_hash']
        for field in required_fields:
            self.assertIn(field, file_data)
        
        # Check data types
        self.assertIsInstance(file_data['id'], int)
        self.assertIsInstance(file_data['original_filename'], str)
        self.assertIsInstance(file_data['uploaded_at'], str)
        self.assertIsInstance(file_data['tags'], list)
        self.assertIsInstance(file_data['size'], int)
        self.assertIsInstance(file_data['file_hash'], str) 