# File Vault System - Technical Documentation

## Overview
File Vault is a secure file storage and management system with user authentication, file deduplication, tagging, and search capabilities. The system is built with Django REST Framework as the backend API, React for the frontend, and uses MySQL for persistent storage.

## Architecture

### Technology Stack
- **Backend**: Django REST Framework
- **Frontend**: React 18 with React Router
- **Database**: MySQL
- **Authentication**: JWT tokens
- **File Storage**: Django's default file storage (configurable)
- **Deployment**: Docker + Docker Compose
- **Web Server**: Gunicorn (backend), Node.js dev server (frontend)

### Core Features
- User registration and JWT-based authentication
- Clean, modern React frontend with responsive design
- File upload with automatic deduplication (SHA-256 based)
- File tagging and search capabilities
- Storage quota management per user
- Soft delete functionality
- File statistics and storage usage tracking
- Background cleanup tasks for orphaned files

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)

### Running with Docker
1. Clone the repository
2. Create a `.env` file based on the example (see Configuration section)
3. Start all services:
```bash
docker compose up --build
```

**Services will be available at:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Database: localhost:3306

### Local Development

#### Backend Only
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run Django development server
python manage.py runserver
```

#### Frontend Only
```bash
cd frontend
npm install
npm start
```

## Frontend Features

### Authentication
- User registration with validation
- Secure login with JWT tokens
- Automatic token refresh
- Protected routes and navigation
- Clean error handling and user feedback

### UI/UX
- Modern, responsive design with Inter font
- Gradient backgrounds and clean card layouts
- Loading states and form validation
- Mobile-friendly responsive design
- Smooth transitions and hover effects

### Current Pages
- **Login** (`/login`): User authentication
- **Register** (`/register`): Account creation
- **Dashboard** (`/dashboard`): User profile and file management (placeholder)

## API Integration

The frontend communicates with the backend through a robust API service:

```javascript
// Authentication
authAPI.register(userData)     // Register new user
authAPI.login(credentials)     // Login user
authAPI.logout(refreshToken)   // Logout user
authAPI.getCurrentUser()       // Get user profile

// Files (ready for future implementation)
fileAPI.getFiles(params)       // List user files
fileAPI.uploadFile(formData)   // Upload new file
fileAPI.downloadFile(fileId)   // Download file
fileAPI.deleteFile(fileId)     // Delete file
```

### Token Management
- Automatic token refresh on API calls
- Secure storage in localStorage
- Automatic logout on refresh failure
- Request/response interceptors for seamless auth

## API Endpoint

### POST `/api/auth/register/`
Register a new user account.

**Request:**
```json
{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "first_name": "Test",
    "last_name": "User"
}
```

**Response (201):**
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

## Test the API

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com", 
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "first_name": "Test",
    "last_name": "User"
  }'
``` 