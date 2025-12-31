# RBAC Implementation - Complete Testing Guide

## Overview

This guide provides step-by-step instructions to test the Role-Based Access Control (RBAC) implementation.

---

## Setup (One-Time)

### 1. Start PostgreSQL Database

```bash
cd d:\itdesk
docker-compose up -d
```

Verify the database is running:
```bash
docker-compose ps
```

Expected output:
```
itdesk-postgres-1   postgres:13   postgres   Up   5432/tcp
itdesk-redis-1      redis:alpine  redis      Up   6379/tcp
itdesk-app-1        ./backend     ...        Up   8000/tcp
```

### 2. Apply Database Migrations

```bash
cd d:\itdesk\backend
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade d11bba1f83d1 -> rbac_001
INFO  [alembic.runtime.migration] Running upgrade rbac_001 -> add_password_001
```

### 3. Seed Initial Data

```bash
cd d:\itdesk\backend
python scripts/seed_rbac.py
```

Expected output:
```
Seeding roles...
Successfully seeded roles:
  - admin: read,write,delete,admin
  - user: read,write
  - viewer: read
Seeding users...
Successfully seeded users:
  - admin: admin@example.com
  - user1: user1@example.com
  - user2: user2@example.com
  - viewer: viewer@example.com

=== RBAC Seeding Finished Successfully ===

Test Credentials:
  Admin User:
    username: admin
    password: admin123
    role: admin (permissions: read,write,delete,admin)
  ...
```

### 4. Start the Application

```bash
cd d:\itdesk\backend
PYTHONPATH=. uvicorn app.main:app --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The API is now available at `http://localhost:8000`

---

## Test 1: Authentication

### Test 1.1 - Login as Admin

**Request:**
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the token:**
```bash
TOKEN="<copy-the-access_token-value>"
```

### Test 1.2 - Login with Wrong Password

**Request:**
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=wrongpassword"
```

**Expected Response:**
```json
{
  "detail": "Incorrect username or password"
}
```

### Test 1.3 - Login with Nonexistent User

**Request:**
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=nonexistent&password=password123"
```

**Expected Response:**
```json
{
  "detail": "Incorrect username or password"
}
```

---

## Test 2: Get Current User Info

### Test 2.1 - Get User Info (Authenticated)

**Request:**
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "permissions": "read,write,delete,admin"
}
```

### Test 2.2 - Get User Info Without Token

**Request:**
```bash
curl -X GET "http://localhost:8000/me"
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```

### Test 2.3 - Get User Info With Invalid Token

**Request:**
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer invalid_token_here"
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## Test 3: Role-Based Access Control

### Test 3.1 - Admin Endpoint (Admin User)

**Request:**
```bash
# First, get admin token
ADMIN_TOKEN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Access admin endpoint
curl -X GET "http://localhost:8000/admin" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "message": "Welcome, admin admin!",
  "role": "admin",
  "permissions": "read,write,delete,admin",
  "email": "admin@example.com"
}
```

### Test 3.2 - Admin Endpoint (Regular User)

**Request:**
```bash
# Get regular user token
USER_TOKEN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=user123" | jq -r '.access_token')

# Try to access admin endpoint
curl -X GET "http://localhost:8000/admin" \
  -H "Authorization: Bearer $USER_TOKEN"
```

**Expected Response:**
```json
{
  "detail": "Not enough permissions"
}
```

### Test 3.3 - Admin Endpoint (Viewer User)

**Request:**
```bash
# Get viewer token
VIEWER_TOKEN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=viewer&password=viewer789" | jq -r '.access_token')

# Try to access admin endpoint
curl -X GET "http://localhost:8000/admin" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Response:**
```json
{
  "detail": "Not enough permissions"
}
```

### Test 3.4 - User-Protected Endpoint

**Request:**
```bash
# Admin user can access
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Regular user can access
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer $USER_TOKEN"

# Viewer cannot access
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Responses:**
- Admin: `{"message": "Hello, admin!", "role": "admin", "permissions": "..."}`
- User: `{"message": "Hello, user1!", "role": "user", "permissions": "..."}`
- Viewer: `{"detail": "Not enough permissions"}`

---

## Test 4: Permission-Based Access Control

### Test 4.1 - Read-Only Endpoint

**Request:**
```bash
# All roles should be able to read
curl -X GET "http://localhost:8000/read-only" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl -X GET "http://localhost:8000/read-only" \
  -H "Authorization: Bearer $USER_TOKEN"

curl -X GET "http://localhost:8000/read-only" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Response:**
```json
{
  "message": "Hello {username}, you have read permission",
  "role": "{role_name}",
  "permissions": "{permissions}"
}
```

All three should succeed.

### Test 4.2 - Write-Resource Endpoint

**Request:**
```bash
# Admin and User should succeed
curl -X POST "http://localhost:8000/write-resource" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl -X POST "http://localhost:8000/write-resource" \
  -H "Authorization: Bearer $USER_TOKEN"

# Viewer should fail
curl -X POST "http://localhost:8000/write-resource" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Responses:**
- Admin: `{"message": "Resource created by admin", "role": "admin", "action": "write"}`
- User: `{"message": "Resource created by user1", "role": "user", "action": "write"}`
- Viewer: `{"detail": "Permission 'write' is required"}`

### Test 4.3 - Delete-Resource Endpoint

**Request:**
```bash
# Only Admin should succeed
curl -X DELETE "http://localhost:8000/admin-delete" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# User should fail (no delete permission)
curl -X DELETE "http://localhost:8000/admin-delete" \
  -H "Authorization: Bearer $USER_TOKEN"

# Viewer should fail
curl -X DELETE "http://localhost:8000/admin-delete" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Responses:**
- Admin: `{"message": "Resource deleted by admin", "role": "admin", "action": "delete"}`
- User: `{"detail": "Permission 'delete' is required"}`
- Viewer: `{"detail": "Permission 'delete' is required"}`

---

## Test 5: Special Endpoints

### Test 5.1 - Users Info (Admin Only)

**Request:**
```bash
# Admin can access
curl -X GET "http://localhost:8000/users-info" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# User cannot access
curl -X GET "http://localhost:8000/users-info" \
  -H "Authorization: Bearer $USER_TOKEN"

# Viewer cannot access
curl -X GET "http://localhost:8000/users-info" \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Responses:**
- Admin: 
  ```json
  {
    "current_user": {
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    },
    "message": "Only admins can see this information"
  }
  ```
- User: `{"detail": "Not enough permissions"}`
- Viewer: `{"detail": "Not enough permissions"}`

---

## Test 6: Edge Cases

### Test 6.1 - Expired Token

**Note:** Default token expiration is 30 minutes. You can test this by:
1. Getting a token
2. Waiting 30 minutes (or modify the config for testing)
3. Try to use the token

**Request:**
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer $EXPIRED_TOKEN"
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

### Test 6.2 - Malformed Token

**Request:**
```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer malformed.token.here"
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

### Test 6.3 - Wrong Bearer Format

**Request:**
```bash
# Missing "Bearer"
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: $ADMIN_TOKEN"
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```

---

## Test 7: Multiple Logins

Test that the same user can get multiple tokens and use them simultaneously.

**Request:**
```bash
# Get first token
TOKEN1=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Get second token (different token, same user)
TOKEN2=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Both tokens should work
curl -X GET "http://localhost:8000/me" -H "Authorization: Bearer $TOKEN1"
curl -X GET "http://localhost:8000/me" -H "Authorization: Bearer $TOKEN2"

# Tokens should be different
echo "Token 1: $TOKEN1"
echo "Token 2: $TOKEN2"
```

**Expected Response:**
- Both tokens should successfully return user info
- Tokens should have different values

---

## Test 8: Automated Test Script

Create a test script `test_rbac.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_endpoint() {
  local name=$1
  local method=$2
  local url=$3
  local token=$4
  local expected_code=$5
  
  if [ -z "$token" ]; then
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url")
  else
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" \
      -H "Authorization: Bearer $token")
  fi
  
  code=$(echo "$response" | tail -n1)
  
  if [ "$code" = "$expected_code" ]; then
    echo -e "${GREEN}✓ PASS${NC}: $name (HTTP $code)"
    ((PASS++))
  else
    echo -e "${RED}✗ FAIL${NC}: $name (Expected $expected_code, got $code)"
    ((FAIL++))
  fi
}

echo "=== RBAC Testing ==="

# Get tokens
echo "Getting tokens..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

USER_TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=user123" | jq -r '.access_token')

VIEWER_TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=viewer&password=viewer789" | jq -r '.access_token')

echo "Testing endpoints..."

# Authentication tests
test_endpoint "Login Success" "POST" "/token" "" "200"
test_endpoint "Get Me (Admin)" "GET" "/me" "$ADMIN_TOKEN" "200"
test_endpoint "Get Me (No Token)" "GET" "/me" "" "403"

# Role-based tests
test_endpoint "Admin Endpoint (Admin)" "GET" "/admin" "$ADMIN_TOKEN" "200"
test_endpoint "Admin Endpoint (User)" "GET" "/admin" "$USER_TOKEN" "403"
test_endpoint "Admin Endpoint (Viewer)" "GET" "/admin" "$VIEWER_TOKEN" "403"

# Permission-based tests
test_endpoint "Read Only (Admin)" "GET" "/read-only" "$ADMIN_TOKEN" "200"
test_endpoint "Read Only (User)" "GET" "/read-only" "$USER_TOKEN" "200"
test_endpoint "Read Only (Viewer)" "GET" "/read-only" "$VIEWER_TOKEN" "200"

test_endpoint "Write Resource (Admin)" "POST" "/write-resource" "$ADMIN_TOKEN" "200"
test_endpoint "Write Resource (User)" "POST" "/write-resource" "$USER_TOKEN" "200"
test_endpoint "Write Resource (Viewer)" "POST" "/write-resource" "$VIEWER_TOKEN" "403"

echo ""
echo "=== Test Results ==="
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}Some tests failed!${NC}"
  exit 1
fi
```

Run the test:
```bash
chmod +x test_rbac.sh
./test_rbac.sh
```

---

## Cleanup

To stop the application and database:

```bash
# Stop the FastAPI server
Ctrl+C

# Stop Docker containers
docker-compose down

# Optional: Remove data volume
docker-compose down -v
```

---

## Success Criteria

✅ All RBAC features working correctly:
- [x] Users can log in with correct credentials
- [x] Users cannot log in with wrong password
- [x] Tokens are validated properly
- [x] Admin users can access admin endpoints
- [x] Regular users cannot access admin endpoints
- [x] Viewer users cannot access endpoints requiring write/delete permissions
- [x] All permission-based checks work correctly
- [x] Errors return appropriate HTTP status codes

---

## Troubleshooting

### Database Connection Error
```
psycopg2.OperationalError: connection refused
```
**Solution:** Ensure PostgreSQL is running with `docker-compose ps`

### Token Validation Error
```
"detail": "Could not validate credentials"
```
**Solutions:**
- Check token format: `Authorization: Bearer <token>`
- Verify token hasn't expired
- Confirm SECRET_KEY matches what was used to create token

### "Not enough permissions"
```
"detail": "Not enough permissions"
```
**Solution:** User doesn't have the required role, try with admin token

### Database Already Seeded
```
Roles already exist in the database.
```
**Solution:** This is normal if running seed script multiple times. Database already has data.

---

## Next Steps

After successful testing:
1. Review the RBAC implementation in the code
2. Read the [RBAC.md](RBAC.md) documentation
3. Check the [RBAC_QUICK_REFERENCE.md](RBAC_QUICK_REFERENCE.md) for quick reference
4. Consider production deployment changes (change SECRET_KEY, update DATABASE_URL, etc.)
