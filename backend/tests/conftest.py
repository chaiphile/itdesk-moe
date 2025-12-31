"""Pytest configuration and fixtures for testing."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, get_db
from app.models.models import Role, User, Team, Ticket


# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with a fresh database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client without running startup events
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_role(db):
    """Create a sample role for testing."""
    role = Role(name="admin", permissions="read,write,delete")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def sample_user(db, sample_role):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        role_id=sample_role.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_team(db):
    """Create a sample team for testing."""
    team = Team(name="Support Team", description="Main support team")
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@pytest.fixture
def sample_ticket(db, sample_user, sample_team):
    """Create a sample ticket for testing."""
    ticket = Ticket(
        title="Test Ticket",
        description="This is a test ticket",
        status="open",
        priority="high",
        user_id=sample_user.id,
        team_id=sample_team.id
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
