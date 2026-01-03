"""Tests for database models and operations."""

import pytest
from app.models.models import Role, Team, Ticket, User
from sqlalchemy.exc import IntegrityError


class TestRoleModel:
    """Test Role model."""

    def test_create_role(self, db):
        """Test creating a role."""
        role = Role(name="admin", permissions="read,write,delete")
        db.add(role)
        db.commit()
        db.refresh(role)

        assert role.id is not None
        assert role.name == "admin"
        assert role.permissions == "read,write,delete"

    def test_role_unique_name(self, db, sample_role):
        """Test that role names must be unique."""
        duplicate_role = Role(name="admin", permissions="read")
        db.add(duplicate_role)

        with pytest.raises(IntegrityError):
            db.commit()

    def test_role_users_relationship(self, db, sample_role, sample_user):
        """Test role-user relationship."""
        db.refresh(sample_role)
        assert len(sample_role.users) == 1
        assert sample_role.users[0].username == "testuser"


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db, sample_role):
        """Test creating a user."""
        user = User(username="newuser", email="new@example.com", role_id=sample_role.id)
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.role_id == sample_role.id

    def test_user_unique_username(self, db, sample_user):
        """Test that usernames must be unique."""
        duplicate_user = User(
            username="testuser",
            email="different@example.com",
            role_id=sample_user.role_id,
        )
        db.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_unique_email(self, db, sample_user):
        """Test that emails must be unique."""
        duplicate_user = User(
            username="differentuser",
            email="test@example.com",
            role_id=sample_user.role_id,
        )
        db.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_role_relationship(self, db, sample_user, sample_role):
        """Test user-role relationship."""
        assert sample_user.role.name == "admin"
        assert sample_user.role_id == sample_role.id


class TestTeamModel:
    """Test Team model."""

    def test_create_team(self, db):
        """Test creating a team."""
        team = Team(name="Engineering", description="Engineering team")
        db.add(team)
        db.commit()
        db.refresh(team)

        assert team.id is not None
        assert team.name == "Engineering"
        assert team.description == "Engineering team"

    def test_team_unique_name(self, db, sample_team):
        """Test that team names must be unique."""
        duplicate_team = Team(name="Support Team", description="Different team")
        db.add(duplicate_team)

        with pytest.raises(IntegrityError):
            db.commit()


class TestTicketModel:
    """Test Ticket model."""

    def test_create_ticket(self, db, sample_user, sample_team):
        """Test creating a ticket."""
        ticket = Ticket(
            title="Bug Report",
            description="Found a bug in the system",
            status="OPEN",
            priority="HIGH",
            user_id=sample_user.id,
            team_id=sample_team.id,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        assert ticket.id is not None
        assert ticket.title == "Bug Report"
        assert ticket.status == "OPEN"
        assert ticket.priority == "HIGH"

    def test_ticket_default_status(self, db, sample_user):
        """Test ticket default status."""
        ticket = Ticket(title="New Ticket", description="Test", user_id=sample_user.id)
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        assert ticket.status == "OPEN"
        assert ticket.priority == "MED"

    def test_ticket_user_relationship(self, db, sample_ticket, sample_user):
        """Test ticket-user relationship."""
        assert sample_ticket.user.username == "testuser"
        assert sample_ticket.user_id == sample_user.id

    def test_ticket_team_relationship(self, db, sample_ticket, sample_team):
        """Test ticket-team relationship."""
        assert sample_ticket.team.name == "Support Team"
        assert sample_ticket.team_id == sample_team.id
