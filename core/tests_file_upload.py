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

    def test_large_file_rejection(self):
        """Test rejection of files exceeding size limit"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create a file larger than the limit (assuming 100MB limit)
        # Use a smaller size for testing (1MB) and mock the limit
        large_content = b"x" * (1024 * 1024)  # 1MB content
        large_file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")
        
        # Mock the environment variable to set a smaller limit for testing
        import os
        original_limit = os.environ.get('MAX_FILE_SIZE_MB', '100')
        os.environ['MAX_FILE_SIZE_MB'] = '0'  # Set to 0MB to force rejection
        
        try:
            data = {'file': large_file}
            response = self.client.post(self.upload_url, data, format='multipart')
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('File size cannot exceed', str(response.data))
        finally:
            # Restore original limit
            os.environ['MAX_FILE_SIZE_MB'] = original_limit

    def test_file_soft_delete_and_undelete(self):
        """Test file soft delete and undelete functionality"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Get user's initial storage usage before upload
        initial_storage_used = self.user.storage_used
        
        # Upload a file
        upload_data = {
            'file': SimpleUploadedFile("test_delete.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['delete-test'])
        }
        upload_response = self.client.post(self.upload_url, upload_data, format='multipart')
        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        
        file_id = upload_response.data['id']
        
        # Verify file exists and is not deleted
        user_file = UserFile.objects.get(id=file_id)
        self.assertFalse(user_file.deleted)
        
        file_size = user_file.file.size
        
        # Verify storage usage increased after upload
        self.user.refresh_from_db()
        self.assertEqual(self.user.storage_used, initial_storage_used + file_size)
        
        # Delete the file
        delete_url = reverse('file_delete', kwargs={'file_id': file_id})
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify file is soft deleted
        user_file.refresh_from_db()
        self.assertTrue(user_file.deleted)
        
        # Verify storage usage was updated (should be back to initial)
        self.user.refresh_from_db()
        self.assertEqual(self.user.storage_used, initial_storage_used)
        
        # Verify file doesn't appear in file list
        list_url = reverse('file_list')
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        file_ids = [f['id'] for f in list_response.data['results']]
        self.assertNotIn(file_id, file_ids)
        
        # Upload the same file again (should undelete)
        undelete_data = {
            'file': SimpleUploadedFile("test_delete.txt", self.test_file_content, content_type="text/plain"),
            'tags': json.dumps(['undelete-test'])
        }
        undelete_response = self.client.post(self.upload_url, undelete_data, format='multipart')
        self.assertEqual(undelete_response.status_code, status.HTTP_201_CREATED)
        
        # Should return the same file ID (undeleted)
        self.assertEqual(undelete_response.data['id'], file_id)
        
        # Verify file is undeleted
        user_file.refresh_from_db()
        self.assertFalse(user_file.deleted)
        self.assertEqual(user_file.tags, ['undelete-test'])  # Tags should be updated
        
        # Verify storage usage was restored (back to having the file)
        self.user.refresh_from_db()
        self.assertEqual(self.user.storage_used, initial_storage_used + file_size)
        
        # Verify file appears in file list again
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        file_ids = [f['id'] for f in list_response.data['results']]
        self.assertIn(file_id, file_ids)

    def test_delete_nonexistent_file(self):
        """Test deleting a non-existent file"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        delete_url = reverse('file_delete', kwargs={'file_id': 99999})
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'File not found')

    def test_delete_already_deleted_file(self):
        """Test deleting an already deleted file"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Upload and delete a file
        upload_data = {
            'file': SimpleUploadedFile("test_double_delete.txt", self.test_file_content, content_type="text/plain"),
        }
        upload_response = self.client.post(self.upload_url, upload_data, format='multipart')
        file_id = upload_response.data['id']
        
        # Delete the file
        delete_url = reverse('file_delete', kwargs={'file_id': file_id})
        self.client.delete(delete_url)
        
        # Try to delete again
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_unauthorized(self):
        """Test deleting a file without authentication"""
        delete_url = reverse('file_delete', kwargs={'file_id': 1})
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_undelete_with_different_user(self):
        """Test that undelete only works for the same user"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Upload and delete a file as first user
        upload_data = {
            'file': SimpleUploadedFile("user_test.txt", self.test_file_content, content_type="text/plain"),
        }
        upload_response = self.client.post(self.upload_url, upload_data, format='multipart')
        file_id = upload_response.data['id']
        
        delete_url = reverse('file_delete', kwargs={'file_id': file_id})
        self.client.delete(delete_url)
        
        # Create second user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com', 
            password='testpass123'
        )
        refresh2 = RefreshToken.for_user(user2)
        access_token2 = str(refresh2.access_token)
        
        # Try to upload same file as second user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token2}')
        upload_data2 = {
            'file': SimpleUploadedFile("user_test.txt", self.test_file_content, content_type="text/plain"),
        }
        response2 = self.client.post(self.upload_url, upload_data2, format='multipart')
        
        # Should create a new UserFile association, not undelete the first user's file
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response2.data['id'], file_id)
        
        # Verify first user's file is still deleted
        user_file1 = UserFile.objects.get(id=file_id)
        self.assertTrue(user_file1.deleted)
