"""
Core App Test Suite

This module imports all test classes from the organized test files:
- tests_auth.py: Authentication tests (registration, login, logout, token refresh)
- tests_file_upload.py: File upload tests (upload, validation, deduplication)
- tests_file_list.py: File listing tests (search, filtering, pagination)

Usage:
    # Run all tests
    python manage.py test core

    # Run specific test class
    python manage.py test core.tests.AuthenticationAPITests

    # Run specific test method
    python manage.py test core.tests.AuthenticationAPITests.test_user_registration_success
"""

# Import all test classes from separate test files
from .tests_auth import AuthenticationAPITests
from .tests_file_upload import FileUploadAPITests  
from .tests_file_list import FileListAPITests

# Make test classes available in this module
__all__ = [
    'AuthenticationAPITests',
    'FileUploadAPITests', 
    'FileListAPITests',
] 