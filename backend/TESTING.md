# Testing Guide

## Overview

This project includes a comprehensive test suite covering:
- **Database Models**: Tests for all SQLAlchemy models (Role, User, Team, Ticket)
- **Database Connection**: Tests for database connectivity and operations
- **API Endpoints**: Tests for FastAPI endpoints
- **Relationships**: Tests for model relationships and constraints

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Pytest fixtures and configuration
├── test_models.py        # Model tests
├── test_db_connection.py # Database connection tests
└── test_api.py          # API endpoint tests
```

## Setup

### Install Test Dependencies

```bash
cd backend
pip install -e ".[dev]"
```

This installs the project with development dependencies including pytest and httpx.

### Database Configuration for Testing

The test suite uses **SQLite in-memory database** for testing instead of PostgreSQL. This provides:
- ✅ Fast test execution
- ✅ No external dependencies
- ✅ Isolated test environments
- ✅ Automatic cleanup between tests

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_models.py
```

### Run Specific Test Class
```bash
pytest tests/test_models.py::TestUserModel
```

### Run Specific Test
```bash
pytest tests/test_models.py::TestUserModel::test_create_user
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage Report
```bash
pip install pytest-cov
pytest --cov=app tests/
```

### Run Tests in Parallel (faster)
```bash
pip install pytest-xdist
pytest -n auto
```

## Test Coverage

### Model Tests (`test_models.py`)
- ✅ Role creation and uniqueness
- ✅ User creation with role relationships
- ✅ Team creation and uniqueness
- ✅ Ticket creation with default values
- ✅ Model relationships (foreign keys)
- ✅ Constraint validation (unique fields)

### Database Connection Tests (`test_db_connection.py`)
- ✅ Database connection verification
- ✅ Session creation
- ✅ Table existence validation
- ✅ Relationship integrity
- ✅ Query operations (SELECT, COUNT, FILTER)
- ✅ Transaction rollback

### API Tests (`test_api.py`)
- ✅ Ping endpoint
- ✅ Health check endpoint
- ✅ Auth endpoints availability
- ✅ Admin endpoints availability

## Fixtures

The `conftest.py` file provides reusable fixtures:

### `db`
Fresh database session for each test
```python
def test_something(db):
    # db is a clean SQLAlchemy session
    pass
```

### `client`
FastAPI test client with overridden database dependency
```python
def test_api(client):
    response = client.get("/ping")
    assert response.status_code == 200
```

### `sample_role`, `sample_user`, `sample_team`, `sample_ticket`
Pre-created test data
```python
def test_with_data(sample_user, sample_ticket):
    assert sample_ticket.user.username == "testuser"
```

## Database Issue Resolution

### Issue: PostgreSQL Connection Failure

**Problem**: The application is configured to use PostgreSQL, but the database might not be running or credentials are incorrect.

**Solution**: 
1. **For Development**: Use SQLite (tests use this by default)
2. **For Production**: Ensure PostgreSQL is running:
   ```bash
   # Using Docker
   docker-compose up -d
   
   # Or verify PostgreSQL service is running
   ```

3. **Check Connection String** in `.env`:
    ```
    DATABASE_URL=postgresql://proteges:change_me@localhost:5432/ticketing_db
    ```

4. **Verify Database Exists**:
   ```bash
   psql -U proteges -h localhost -d ticketing_db
   ```

### Running with SQLite for Development

To use SQLite instead of PostgreSQL for development:

1. Update `.env`:
   ```
   DATABASE_URL=sqlite:///./test.db
   ```

2. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Continuous Integration

To run tests in CI/CD pipeline:

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=app --cov-report=xml tests/

# Run tests with JUnit XML output
pytest --junit-xml=test-results.xml tests/
```

## Troubleshooting

### Tests Fail with "No module named 'app'"
Ensure you're in the `backend` directory and have installed the package:
```bash
cd backend
pip install -e .
```

### Tests Fail with "Database is locked"
This shouldn't happen with SQLite in-memory, but if using file-based SQLite:
```bash
rm test.db
pytest
```

### Tests Timeout
Run with increased timeout:
```bash
pytest --timeout=300
```

## Best Practices

1. **Use Fixtures**: Leverage provided fixtures instead of creating test data manually
2. **Test Isolation**: Each test should be independent and not rely on others
3. **Clear Names**: Use descriptive test names that explain what is being tested
4. **Arrange-Act-Assert**: Structure tests with clear setup, action, and verification
5. **Mock External Services**: Mock external APIs and services in tests

## Example Test

```python
def test_user_creation(db, sample_role):
    """Test creating a user with a role."""
    # Arrange
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "role_id": sample_role.id
    }
    
    # Act
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Assert
    assert user.id is not None
    assert user.username == "newuser"
    assert user.role.name == "admin"
```

## Next Steps

1. Run the test suite: `pytest`
2. Check coverage: `pytest --cov=app`
3. Add more tests for your specific business logic
4. Integrate tests into your CI/CD pipeline
