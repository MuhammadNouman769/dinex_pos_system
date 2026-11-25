# MN Kitchen POS API Access

Base URL:

```text
http://127.0.0.1:8000
```

## Authentication

### 1. Django Admin

Use the Django Admin panel to manage the platform user.

```text
http://127.0.0.1:8000/admin/
```

### 2. JWT Login

Use the platform user's username and password to obtain JWT tokens.

```text
POST http://127.0.0.1:8000/api/v1/auth/token/
```

Request:

```json
{
    "username": "platform",
    "password": "your-password"
}
```

Response contains:

```json
{
    "refresh": "YOUR_REFRESH_TOKEN",
    "access": "YOUR_ACCESS_TOKEN"
}
```

### 3. Refresh JWT

Use the refresh token to obtain a new access token.

```text
POST http://127.0.0.1:8000/api/v1/auth/token/refresh/
```

Request:

```json
{
    "refresh": "YOUR_REFRESH_TOKEN"
}
```

## Swagger / OpenAPI

### Swagger UI

```text
http://127.0.0.1:8000/api/docs/
```

### OpenAPI Schema

```text
http://127.0.0.1:8000/api/schema/
```

## Onboarding

### Create Restaurant

This endpoint is used by an authenticated platform user for the first-time restaurant setup.

```text
POST http://127.0.0.1:8000/api/v1/onboarding/restaurant/
```

Authentication:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Request:

```json
{
    "organization": {
        "name": "The Makar",
        "currency": "PKR",
        "timezone": "Asia/Karachi"
    },
    "owner": {
        "username": "usama",
        "email": "usama@example.com",
        "password": "secure-password",
        "first_name": "Usama",
        "last_name": "Shafaqat"
    },
    "location": {
        "name": "Main Branch",
        "address": "Islamabad, Pakistan",
        "phone": "03001234567",
        "is_primary": true
    }
}
```

Backend transaction:

```text
BEGIN TRANSACTION

Create Owner User
        ↓
Create Organization
        ↓
Create OrganizationMembership
        role = OWNER
        ↓
Create Location
        ↓
COMMIT
```

If any step fails:

```text
ROLLBACK
```

No partial restaurant setup should remain in the database.

### Check Onboarding Status

```text
GET http://127.0.0.1:8000/api/v1/onboarding/status/
```

Authentication:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Example response:

```json
{
    "completed": false,
    "organization_created": true,
    "owner_created": true,
    "location_created": false,
    "next_step": "LOCATION"
}
```

## API Flow

```text
1. Open Django Admin
        ↓
   /admin/

2. Platform user exists
        ↓
   Platform Login

3. Obtain JWT
        ↓
   POST /api/v1/auth/token/

4. Open Swagger
        ↓
   /api/docs/

5. Click Authorize
        ↓
   Bearer <access_token>

6. Create restaurant
        ↓
   POST /api/v1/onboarding/restaurant/

7. Check onboarding status
        ↓
   GET /api/v1/onboarding/status/
```

## Quick URL List

| Purpose | Method | URL |
|---|---|---|
| Django Admin | GET | `/admin/` |
| JWT Login | POST | `/api/v1/auth/token/` |
| JWT Refresh | POST | `/api/v1/auth/token/refresh/` |
| Swagger UI | GET | `/api/docs/` |
| OpenAPI Schema | GET | `/api/schema/` |
| Create Restaurant | POST | `/api/v1/onboarding/restaurant/` |
| Onboarding Status | GET | `/api/v1/onboarding/status/` |

## Important

For local development, replace the base URL with:

```text
http://127.0.0.1:8000
```

For production, replace it with the production API domain.

All protected API endpoints require:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Never commit real passwords, JWT tokens, secret keys, or production credentials to Git.
