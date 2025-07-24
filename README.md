# File Vault - User Registration API

Minimal Django REST API for user registration with JWT authentication.

## Quick Start

1. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your preferred values (defaults should work for development).

2. **Start the services:**
   ```bash
   docker compose up --build
   ```

3. **The API will be available at:**
   - Backend: http://localhost:8000

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