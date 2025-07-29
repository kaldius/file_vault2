# File Vault System - Technical Documentation

## Overview
File Vault is a secure file storage and management system with user authentication, file deduplication, tagging, and search capabilities. The system is built with Django REST Framework as the backend API and uses MySQL for persistent storage.

## Architecture

### Technology Stack
- **Backend**: Django
- **Database**: MySQL
- **Authentication**: JWT tokens
- **File Storage**: Django's default file storage (configurable)
- **Deployment**: Docker + Docker Compose
- **Web Server**: Gunicorn

### Core Features
- User registration and JWT-based authentication
- File upload with automatic deduplication (SHA-256 based)
- File tagging and search capabilities
- Storage quota management per user
- Soft delete functionality
- File statistics and storage usage tracking
- Background cleanup tasks for orphaned files

## Database Schema

### Core User Model (`core_user`)
```sql
CREATE TABLE core_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME(6),
    is_superuser BOOLEAN NOT NULL DEFAULT 0,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    email VARCHAR(254) UNIQUE NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    date_joined DATETIME(6) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    storage_quota BIGINT NOT NULL DEFAULT 1073741824, -- 1GB default
    storage_used BIGINT NOT NULL DEFAULT 0
);
```

### File Storage Model (`files`)
```sql
CREATE TABLE files (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA-256 hash for deduplication
    size BIGINT NOT NULL,              -- File size in bytes
    storage_path TEXT NOT NULL,        -- Physical storage path
    mime_type VARCHAR(255),            -- MIME type
    created_at DATETIME(6) NOT NULL,
    
    INDEX idx_hash (hash),
    INDEX idx_size (size),
    INDEX idx_mime_type (mime_type)
);
```

### User File Association Model (`user_files`)
```sql
CREATE TABLE user_files (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    file_id BIGINT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    uploaded_at DATETIME(6) NOT NULL,
    tags JSON DEFAULT '[]',            -- Searchable tags as JSON array
    deleted BOOLEAN NOT NULL DEFAULT 0, -- Soft delete flag
    
    FOREIGN KEY (user_id) REFERENCES core_user(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_user_file_name (user_id, file_id, original_filename),
    INDEX idx_user_deleted (user_id, deleted),
    INDEX idx_uploaded_at (uploaded_at),
    INDEX idx_original_filename (original_filename),
    INDEX idx_deleted (deleted)
);
```

## API Endpoints

### Authentication Endpoints (`/api/auth/`)

#### POST `/api/auth/register/`
**Purpose**: Register a new user account
**Authentication**: Not required
**Status**: ✅ Implemented and working
**Request Body**:
```json
{
    "username": "string",
    "email": "email",
    "password": "string",
    "password_confirm": "string",
    "first_name": "string",
    "last_name": "string"
}
```
**Response (201)**:
```json
{
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    },
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
}
```

#### POST `/api/auth/login/`
**Purpose**: Authenticate user and get JWT tokens
**Authentication**: Not required
**Status**: ✅ Implemented and working
**Request Body**:
```json
{
    "username": "string",
    "password": "string"
}
```
**Response (200)**:
```json
{
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User"
    },
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
}
```

#### POST `/api/auth/logout/`
**Purpose**: Blacklist refresh token (logout)
**Authentication**: Required
**Status**: ✅ Implemented and working
**Request Body**:
```json
{
    "refresh": "jwt_refresh_token"
}
```
**Response (205)**: No content

#### POST `/api/auth/token/refresh/`
**Purpose**: Refresh access token using refresh token
**Authentication**: Not required
**Status**: ✅ Implemented and working
**Request Body**:
```json
{
    "refresh": "jwt_refresh_token"
}
```
**Response (200)**:
```json
{
    "access": "new_jwt_access_token",
    "refresh": "new_jwt_refresh_token"
}
```

### User Management Endpoints (`/api/users/`)

#### GET `/api/users/me/`
**Purpose**: Get current user's profile information
**Authentication**: Required
**Status**: ✅ Implemented and working
**Response (200)**:
```json
{
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "created_at": "2023-07-23T09:50:00Z",
    "storage_quota": 1073741824,
    "storage_used": 1024000
}
```

### File Management Endpoints (`/api/files/`)

#### POST `/api/files/upload/`
**Purpose**: Upload a new file with automatic deduplication
**Authentication**: Required
**Status**: ✅ Implemented and working
**Request**: Multipart form data
- `file`: File upload
- `tags`: JSON array of strings (optional)

**Response (201)**:
```json
{
    "id": 1,
    "original_filename": "document.pdf",
    "uploaded_at": "2023-07-23T10:00:00Z",
    "tags": ["document", "important"],
    "size": 1024000,
    "mime_type": "application/pdf",
    "file_hash": "sha256_hash_string"
}
```

#### GET `/api/files/`
**Purpose**: List user's files with search and filtering
**Authentication**: Required
**Status**: ✅ Implemented and working
**Query Parameters**:
- `search`: Search in filename and tags
- `tags`: Filter by specific tag
- `filename`: Filter by filename (case-insensitive contains)
- `mime_type`: Filter by MIME type
- `size_min`: Minimum file size in bytes
- `size_max`: Maximum file size in bytes
- `uploaded_after`: Filter files uploaded after date
- `uploaded_before`: Filter files uploaded before date
- `ordering`: Sort by field (e.g., `-uploaded_at`, `original_filename`, `file__size`)
- `page`: Page number for pagination

**Response (200)**:
```json
{
    "count": 100,
    "next": "http://localhost:8000/api/files/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "original_filename": "document.pdf",
            "uploaded_at": "2023-07-23T10:00:00Z",
            "tags": ["document"],
            "size": 1024000,
            "mime_type": "application/pdf",
            "file_hash": "sha256_hash"
        }
    ]
}
```

#### GET `/api/files/{id}/`
**Purpose**: Get detailed information about a specific file
**Authentication**: Required
**Status**: ✅ Implemented and working
**Response (200)**: Same as upload response format

#### GET `/api/files/{id}/download/`
**Purpose**: Download file content
**Authentication**: Required
**Status**: ✅ Implemented and working
**Response (200)**: File content with appropriate headers
- `Content-Type`: File's MIME type
- `Content-Disposition`: `attachment; filename="original_filename"`
- `Content-Length`: File size

**Behavior**:
- Returns the actual file content as a downloadable response
- Validates that the user owns the file and it's not deleted
- Returns 404 if file not found, not owned by user, or file missing from storage
- Sets appropriate headers for file download

#### DELETE `/api/files/{id}/delete/`
**Purpose**: Soft delete a user file (removes association, not physical file)
**Authentication**: Required
**Status**: ✅ Implemented and working
**Response (204)**: No content

**Behavior**:
- Sets the `deleted` flag to `True` for the user file association
- Updates user's storage usage by subtracting the file size
- Does not delete the physical file (allows for deduplication and undelete)
- Returns 404 if file not found or already deleted
- Only the file owner can delete their own files

**Undelete Functionality**:
When a user uploads the same file (same content hash and filename) again after deletion:
- The system automatically "undeletes" the existing association
- Sets `deleted` flag back to `False`
- Updates the tags with new values if provided
- Restores the file size to user's storage usage
- Returns the same `UserFile` ID as before deletion

## Key Implementation Details

### File Deduplication
- Files are deduplicated using SHA-256 hashing
- Physical files are stored once in `files/` table
- User associations are tracked in `user_files/` table
- Storage path format: `files/{hash[:2]}/{hash[2:4]}/{hash}`

### Authentication & Authorization
- JWT-based authentication using `djangorestframework-simplejwt`
- Requires `rest_framework_simplejwt.token_blacklist` app for logout functionality
- Access tokens expire in 60 minutes
- Refresh tokens expire in 7 days with rotation
- Token blacklisting on logout prevents token reuse
- All file endpoints require authentication
- Users can only access their own files

### Storage Management
- Default quota: 1GB per user (configurable)
- Storage usage tracked in real-time during upload/delete
- Soft delete preserves file associations for recovery
- Background cleanup task removes orphaned physical files

### Search & Filtering
- Full-text search across filenames and tags
- Advanced filtering by size, date, MIME type, tags
- Pagination with 20 items per page
- Multiple sorting options

### File Upload Constraints
- Maximum file size: 100MB (configurable in serializer)
- Maximum tag length: 50 characters each
- Tags stored as JSON array for flexible querying
- MIME type detection and storage

## Configuration

### Environment Variables
```env
SECRET_KEY=django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=file_vault
DB_USER=root
DB_PASSWORD=password
DB_HOST=db
DB_PORT=3306
USE_SQLITE=False  # Set to True for SQLite fallback
```

### Storage Settings
- File upload max memory size: 5MB
- Temporary upload directory: `/tmp/`
- Media files directory: `media/`
- Static files directory: `staticfiles/`

## Background Tasks

### Cleanup Command
```bash
python manage.py cleanup_files [--dry-run]
```
- Removes orphaned files that have no active user associations
- Only deletes files where all `user_files` entries have `deleted=True`
- Supports dry-run mode for safe testing
- Should be run periodically via cron job

## Deployment

### Docker Compose Setup
```bash
docker compose up --build
```

**Services**:
- `db`: MySQL
- `web`: Django application server (Gunicorn)
- `frontend`: React frontend (if included)

**Volumes**:
- `mysql_data`: Persistent database storage
- `./media`: File storage
- `./staticfiles`: Static assets

### Production Considerations
- Use external storage service (AWS S3, etc.) for file storage
- Implement proper backup strategies for database and files
- Set up monitoring for storage usage and performance
- Configure proper logging and error tracking
- Use environment-specific settings for different deployment stages
- Implement rate limiting for file uploads
- Add virus scanning for uploaded files
- Set up CDN for file downloads if needed

## Security Features
- Password validation with Django's built-in validators
- CORS protection with specific allowed origins
- JWT token blacklisting on logout
- File access control (users can only access their own files)
- SQL injection protection via Django ORM
- XSS protection via REST framework serializers

## Testing
The system includes comprehensive API tests in `core/tests.py` covering:

### Authentication Tests (22 test cases)
- **Registration**: Success, password validation, duplicate checks, missing fields
- **Login**: Success, invalid credentials, inactive users, missing fields  
- **Logout**: Success, invalid tokens, authentication required
- **Token Refresh**: Success, invalid/blacklisted tokens, token rotation
- **Integration**: Complete auth flows, token validation

### Additional Test Coverage
- File upload and deduplication
- Search and filtering functionality
- File download and integrity verification
- Error handling and edge cases
- Storage statistics and quota tracking 