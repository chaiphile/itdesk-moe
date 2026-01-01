# Role-Based Access Control (RBAC) Implementation

## Overview

This document describes the complete RBAC implementation for the FastAPI backend. The system provides role-based and permission-based access control to API endpoints.

## Implementation Components

### 1. Database Models

#### User Model
Location: [app/models/models.py](app/models/models.py#L20)

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="users")
    tickets = relationship("Ticket", back_populates="user")
```

**Features:**
- Unique username and email
- Hashed password storage using bcrypt
- Foreign key to Role for role-based access control
- Automatic timestamp creation

#### Role Model
Location: [app/models/models.py](app/models/models.py#L10)

```python
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    permissions = Column(Text, nullable=True)  # Comma-separated permissions

    # Relationships
    users = relationship("User", back_populates="role")
```

**Default Roles:**
- **admin**: Permissions: `read,write,delete,admin`
- **user**: Permissions: `read,write`
- **viewer**: Permissions: `read`

### 2. Authentication & Authorization

Location: [app/core/auth.py](app/core/auth.py)

#### Key Functions:

**`get_password_hash(password: str) -> str`**
- Hash plain text passwords using bcrypt

**`verify_password(plain_password: str, hashed_password: str) -> bool`**
- Verify a password against its hash

**`authenticate_user(db: Session, username: str, password: str) -> Optional[User]`**
- Authenticate user by username and password
- Returns User if credentials are valid, False otherwise

**`create_access_token(data: dict, expires_delta: Optional[timedelta] = None)`**
- Create JWT access token with expiration
- Uses HS256 algorithm
- Default expiration: 30 minutes

**`get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`**
- FastAPI dependency that extracts and validates JWT token
- Returns current User from token payload
- Raises 401 if token is invalid

**`check_role(required_role: str)`**
- FastAPI dependency factory that checks user's role
- Returns wrapper function for role checking
- Raises 403 if user doesn't have required role
- Example: `current_user: User = Depends(check_role("admin"))`

**`check_permission(required_permission: str)`**
- FastAPI dependency factory that checks user's permissions
- Parses comma-separated permissions from role
- Returns wrapper function for permission checking
- Raises 403 if user doesn't have required permission
- Example: `current_user: User = Depends(check_permission("write"))`

### 3. API Routes

#### Authentication Endpoints
Location: [app/api/routes/auth.py](app/api/routes/auth.py)

**`POST /token`** - Login
- Takes username and password
- Returns JWT access token

**`GET /me`** - Get current user info
- Returns user details and role information
- Requires valid JWT token

#### Protected Endpoints
Location: [app/api/routes/admin.py](app/api/routes/admin.py)

All endpoints require JWT authentication and specific role or permission checks:

**`GET /admin`**
- Requires: `admin` role
- Returns admin greeting and user information

**`GET /protected`**
- Requires: `user` or higher role
- Returns user greeting

**`GET /read-only`**
- Requires: `read` permission
- Any role with read permission can access

**`POST /write-resource`**
- Requires: `write` permission
- Creates a resource

**`DELETE /admin-delete`**
- Requires: `delete` permission
- Deletes a resource (admin only)

**`GET /users-info`**
- Requires: `admin` role
- Admin-only endpoint to view user information

### 4. Database Migrations

The RBAC implementation includes three Alembic migrations:

1. **`d11bba1f83d1_initial_migration.py`** (Initial schema)
   - Creates base tables: users, teams, tickets

2. **`rbac_migration.py`** (RBAC schema)
   - Creates roles table
   - Adds role_id and username fields to users
   - Creates foreign key relationship

3. **`add_password_to_users.py`** (Password field)
   - Adds hashed_password column to users table

**To apply migrations:**
```bash
cd backend
alembic upgrade head
```

### 5. Seed Scripts

#### `scripts/seed_roles.py`
Seed default roles with their permissions.

**Usage:**
```bash
cd backend
python scripts/seed_roles.py
```

**Creates roles:**
- admin (permissions: read,write,delete,admin)
- user (permissions: read,write)
- viewer (permissions: read)

#### `scripts/seed_users.py`
Seed test users with hashed passwords.

**Usage:**
```bash
cd backend
python scripts/seed_users.py
```

**Default test users:**
- admin / admin123
- user1 / user123
- user2 / user456

#### `scripts/seed_rbac.py` (Comprehensive)
Seed both roles and users in a single operation.

**Usage:**
```bash
cd backend
python scripts/seed_rbac.py
```

**Creates:**
- 3 roles (admin, user, viewer)
- 4 test users (admin, user1, user2, viewer)

**Output:**
```
=== RBAC Seeding Finished Successfully ===

Test Credentials:
  Admin User:
    username: admin
    password: admin123
    role: admin (permissions: read,write,delete,admin)

  Regular User:
    username: user1
    password: user123
    role: user (permissions: read,write)

  Viewer User:
    username: viewer
    password: viewer789
    role: viewer (permissions: read)
```

## Setup Instructions

### 1. Database Setup
```bash
cd d:\itdesk
docker-compose up -d  # Start PostgreSQL database
```

### 2. Apply Migrations
```bash
cd d:\itdesk\backend
alembic upgrade head
```

### 3. Seed Initial Data
```bash
cd d:\itdesk\backend
python scripts/seed_rbac.py
```

### 4. Start the Application
```bash
cd d:\itdesk\backend
PYTHONPATH=. uvicorn app.main:app --reload
```

## Usage Examples

### 1. Get JWT Token
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Get Current User Info
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer {access_token}"
```

Response:
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "permissions": "read,write,delete,admin"
}
```

### 3. Access Admin-Only Endpoint
```bash
curl -X GET "http://localhost:8000/admin" \
  -H "Authorization: Bearer {access_token}"
```

Response (admin user):
```json
{
  "message": "Welcome, admin admin!",
  "role": "admin",
  "permissions": "read,write,delete,admin",
  "email": "admin@example.com"
}
```

Response (regular user):
```json
{
  "detail": "Not enough permissions"
}
```

### 4. Access Permission-Based Endpoint
```bash
curl -X POST "http://localhost:8000/write-resource" \
  -H "Authorization: Bearer {access_token}"
```

Response:
```json
{
  "message": "Resource created by {username}",
  "role": "user",
  "action": "write"
}
```

## Security Best Practices

1. **Password Hashing**: All passwords are hashed using bcrypt before storage
2. **JWT Tokens**: Short-lived tokens (30 minutes default) for secure API access
3. **Role-Based Access**: Fine-grained control over API endpoints
4. **Permission Checking**: Additional layer of security via permission validation
5. **Database Relationships**: Proper foreign keys prevent orphaned records

## Configuration

Key settings in [app/core/config.py](app/core/config.py):

```python
# Authentication
SECRET_KEY: str = "your-secret-key-here-change-in-production"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Database
DATABASE_URL: str = "postgresql://postgres:change_me@localhost:5432/ticketing_db"
```

**Note:** Change `SECRET_KEY` in production environments!

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── admin.py          # Protected RBAC endpoints
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   └── ...
│   │   └── router.py             # API router configuration
│   ├── core/
│   │   ├── auth.py               # Auth functions & dependencies
│   │   └── config.py             # Application configuration
│   ├── models/
│   │   └── models.py             # SQLAlchemy models (User, Role)
│   ├── db/
│   │   └── session.py            # Database session setup
│   └── main.py                   # FastAPI application
├── scripts/
│   ├── seed_roles.py             # Seed roles
│   ├── seed_users.py             # Seed users
│   └── seed_rbac.py              # Seed both
└── alembic/
    ├── env.py                    # Alembic environment
    └── versions/
        ├── d11bba1f83d1_initial_migration.py
        ├── rbac_migration.py
        └── add_password_to_users.py
```

## Troubleshooting

### Database Connection Error
Ensure PostgreSQL is running:
```bash
docker-compose ps
```

### Authentication Errors
- Check JWT token expiration (default 30 minutes)
- Verify correct credentials are used
- Ensure user has appropriate role assigned

### Permission Denied
- Check user's role and assigned permissions
- Verify endpoint requires the correct role/permission
- Compare comma-separated permissions string with requirements

## Future Enhancements

1. OAuth2 integration
2. Multi-factor authentication
3. Token refresh endpoints
4. Role hierarchies
5. Dynamic permission management
6. Audit logging
