# Postman API Collection Setup

## Import OpenAPI Schema into Postman

1. Open Postman
2. Click **Import**
3. Enter: `http://localhost:8000/openapi.json`

---

## Setup Environment Variables

1. Go to **Environments** in the left sidebar
2. Click **Import** → Upload `marketplace-environment.json`
3. Select the environment from the dropdown (top right)

---

## Authentication Workflow

### 1. Register a User
- **Endpoint**: `POST /api/auth/register`
- **Body**:
  ```json
  {
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword",
    "full_name": "Test User"
  }
  ```

### 2. Login to Get Token
- **Endpoint**: `POST /api/auth/login`
- **Body**:
  ```json
  {
    "username": "testuser",
    "password": "securepassword"
  }
  ```
- **Copy** the `bearerToken` from the response

### 3. Set Token in Environment
- Click on your environment (top right)
- Add/Update variable:
  - **Variable**: `bearerToken`
  - **Value**: `<paste-your-token-here>`
  - **Type**: `secret`

### 4. Use Token in Requests
The collection is configured to automatically use `{{bearerToken}}` in the Authorization header.

---

## Documentation URLs

| URL | Purpose | Best For |
|-----|---------|----------|
| http://localhost:8000/docs | Swagger UI - Interactive testing | Development & Testing |
| http://localhost:8000/redoc | ReDoc - Clean documentation | Reading & Client sharing |
| http://localhost:8000/openapi.json | OpenAPI Schema (JSON) | Import into tools |

---

## Quick Testing Workflow

1. **Health Check**: `GET /health` - Verify API is running
2. **Register**: `POST /api/auth/register` - Create test user
3. **Login**: `POST /api/auth/login` - Get access token
4. **Set Token**: Update `bearerToken` in environment
5. **Test Protected Endpoints**: Try any authenticated endpoint

---
