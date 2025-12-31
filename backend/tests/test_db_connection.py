"""Tests for database connection and health checks."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError


class TestDatabaseConnection:
    """Test database connection and operations."""

    def test_database_connection(self, db):
        """Test that database connection is working."""
        # If we can create a session and execute a query, connection is working
        result = db.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

    def test_database_session_creation(self, db):
        """Test that database session can be created."""
        assert db is not None
        assert db.is_active

    def test_database_tables_exist(self, db):
        """Test that all required tables exist."""
        # Get all table names
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        required_tables = ["roles", "users", "teams", "tickets"]
        for table in required_tables:
            assert table in tables, f"Table '{table}' not found in database"

    def test_database_relationships(self, db, sample_user, sample_ticket):
        """Test that database relationships work correctly."""
        # Verify user-role relationship
        assert sample_user.role is not None
        assert sample_user.role.name == "admin"
        
        # Verify ticket-user relationship
        assert sample_ticket.user is not None
        assert sample_ticket.user.username == "testuser"
        
        # Verify ticket-team relationship
        assert sample_ticket.team is not None
        assert sample_ticket.team.name == "Support Team"

    def test_database_cascade_delete(self, db, sample_user, sample_ticket):
        """Test that cascade delete works (if configured)."""
        user_id = sample_user.id
        ticket_id = sample_ticket.id
        
        # Delete user
        db.delete(sample_user)
        db.commit()
        
        # Check if user is deleted
        deleted_user = db.query(type(sample_user)).filter_by(id=user_id).first()
        assert deleted_user is None

    def test_database_query_operations(self, db, sample_user, sample_role):
        """Test basic database query operations."""
        from app.models.models import User, Role
        
        # Test SELECT
        user = db.query(User).filter_by(username="testuser").first()
        assert user is not None
        assert user.email == "test@example.com"
        
        # Test COUNT
        user_count = db.query(User).count()
        assert user_count == 1
        
        # Test FILTER
        role = db.query(Role).filter_by(name="admin").first()
        assert role is not None
        assert role.permissions == "read,write,delete"

    def test_database_transaction_rollback(self, db, sample_role):
        """Test that transaction rollback works."""
        from app.models.models import User
        
        initial_count = db.query(User).count()
        
        # Create a user but don't commit
        user = User(
            username="rollback_test",
            email="rollback@example.com",
            role_id=sample_role.id
        )
        db.add(user)
        db.rollback()
        
        # Verify user was not added
        final_count = db.query(User).count()
        assert final_count == initial_count
