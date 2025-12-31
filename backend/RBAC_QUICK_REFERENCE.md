# RBAC Quick Reference Guide

## Quick Start

### 1. Start the Database
```bash
cd d:\itdesk
docker-compose up -d
```

### 2. Run Migrations & Seed Data
```bash
cd d:\itdesk\backend
alembic upgrade head
python scripts/seed_rbac.py
```

### 3. Start the API Server
```bash
cd d:\itdesk\backend
PYTHONPATH=. uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

---

## Default Test Users

| Username | Password  | Role   | Permissions        |
|----------|-----------|--------|-------------------|
| admin    | admin123  | admin  | read,write,delete,admin |
| user1    | user123   | user   | read,write        |
| user2    | user456   | user   | read,write        |
| viewer   | viewer789 | viewer | read              |

---

## API Endpoints Reference

### Authentication

**Login (Get Token)**
```
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

**Get Current User**
```
GET /me
Authorization: Bearer {token}
```

### Admin (Role-Based)

**Admin-Only Endpoint**
```
GET /admin
Authorization: Bearer {token}
```
Requires: `admin` role

**Protected User Endpoint**
```
GET /protected
Authorization: Bearer {token}
```
Requires: `user` or higher role

### Permission-Based

**Read-Only Endpoint**
```
GET /read-only
Authorization: Bearer {token}
```
Requires: `read` permission (all roles)

**Create Resource**
```
POST /write-resource
Authorization: Bearer {token}
```
Requires: `write` permission (admin, user)

**Delete Resource**
```
DELETE /admin-delete
Authorization: Bearer {token}
```
Requires: `delete` permission (admin only)

**List Users (Admin)**
```
GET /users-info
Authorization: Bearer {token}
```
Requires: `admin` role

---

## How to Use Role-Based Access Control

### In Your Endpoint

```python
from fastapi import APIRouter, Depends
from app.core.auth import check_role, check_permission, get_current_user
from app.models.models import User

router = APIRouter()

# Check specific role
@router.get("/admin-action")
def admin_action(current_user: User = Depends(check_role("admin"))):
    return {"message": f"Admin {current_user.username} performed action"}

# Check specific permission
@router.post("/create-item")
def create_item(current_user: User = Depends(check_permission("write"))):
    return {"message": f"Item created by {current_user.username}"}

# Just get current user
@router.get("/my-info")
def get_my_info(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role.name,
        "permissions": current_user.role.permissions
    }
```

---

## How to Add New Roles

### Edit the Seed Script

Modify `scripts/seed_rbac.py`:

```python
roles_data = [
    {"name": "admin", "permissions": "read,write,delete,admin"},
    {"name": "user", "permissions": "read,write"},
    {"name": "viewer", "permissions": "read"},
    {"name": "moderator", "permissions": "read,write,delete"},  # New role
]
```

Then run:
```bash
python scripts/seed_rbac.py
```

---

## How to Add New Users

### Using Seed Script

Modify `scripts/seed_rbac.py`:

```python
users_data = [
    {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
        "role_id": user_role.id
    },
    # ... other users
]
```

Then run:
```bash
python scripts/seed_rbac.py
```

---

## How to Create a Role-Protected Endpoint

```python
from fastapi import APIRouter, Depends
from app.core.auth import check_role
from app.models.models import User

router = APIRouter()

@router.get("/secret")
def secret_endpoint(current_user: User = Depends(check_role("admin"))):
    """
    This endpoint only allows users with 'admin' role.
    - Returns 403 if user doesn't have admin role
    - Returns 401 if no valid token provided
    """
    return {"message": "This is secret"}
```

---

## How to Create a Permission-Protected Endpoint

```python
from fastapi import APIRouter, Depends
from app.core.auth import check_permission
from app.models.models import User

router = APIRouter()

@router.delete("/resource/{id}")
def delete_resource(
    id: int,
    current_user: User = Depends(check_permission("delete"))
):
    """
    This endpoint only allows users with 'delete' permission.
    - Currently only 'admin' role has delete permission
    - Returns 403 if user doesn't have delete permission
    - Returns 401 if no valid token provided
    """
    return {"deleted": id}
```

---

## How to Check Permissions in Code

```python
# Role-based check
if current_user.role.name == "admin":
    # Admin-only logic
    pass

# Permission-based check
if "write" in current_user.role.permissions.split(","):
    # Has write permission
    pass

# Check if user exists and has role
if current_user.role:
    permissions = current_user.role.permissions.split(",")
    if "admin" in permissions:
        # Is admin
        pass
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```
**Causes:**
- No token provided
- Invalid/expired token
- Tampered token

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```
**Causes:**
- User doesn't have required role
- User doesn't have required permission
- User has no role assigned

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Causes:**
- Missing required fields
- Invalid data format

---

## Configuration

### Change JWT Expiration

Edit `app/core/config.py`:

```python
class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Change from 30 to 60
```

### Change Secret Key

**IMPORTANT:** Change in production!

Edit `app/core/config.py`:

```python
SECRET_KEY: str = "your-production-secret-key-here"
```

### Change Database URL

Edit `app/core/config.py`:

```python
DATABASE_URL: str = "postgresql://user:password@host:5432/database"
```

---

## Troubleshooting

### "Not enough permissions" but user should have access

1. Check user's role:
   ```bash
   # Login as user, get token
   # Call /me endpoint to see role and permissions
   ```

2. Check endpoint requirements:
   - Verify the permission/role required in endpoint code
   - Compare with user's actual permissions

3. Verify permissions string format:
   - Should be comma-separated: `read,write,delete`
   - No spaces: NOT `read, write, delete`

### "Could not validate credentials"

1. Token expired (default 30 minutes)
   - Get new token via `/token` endpoint

2. Invalid token
   - Ensure token format is correct: `Bearer <token>`
   - Don't include "Bearer" in the token, only in the header

3. Wrong SECRET_KEY
   - If you changed `SECRET_KEY`, old tokens become invalid

### User can't login

1. Check if user exists:
   ```bash
   # Query database or check seed script output
   ```

2. Check password:
   - Passwords are case-sensitive
   - Ensure no typos

3. User has no role:
   - Verify user's `role_id` is set
   - Verify role exists in `roles` table

---

## More Information

See [RBAC.md](RBAC.md) for detailed documentation.
