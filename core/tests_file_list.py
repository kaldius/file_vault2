"""
File Listing API Tests

Test suite for file listing functionality:
- GET /api/files/
"""

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import json
from .models import File, UserFile

User = get_user_model()


class FileListAPITests(APITestCase):
    """Comprehensive test suite for file listing endpoint"""
    
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