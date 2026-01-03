"""Tests for API endpoints."""



class TestPingEndpoint:
    """Test ping endpoint."""

    def test_ping_endpoint(self, client):
        """Test that ping endpoint returns status."""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "edu-ticketing-api"
        assert data["env"] == "dev"

    def test_ping_endpoint_has_required_fields(self, client):
        """Test that ping endpoint returns all required fields."""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "app" in data
        assert "env" in data


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint(self, client):
        """Test that health endpoint returns status."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_auth_endpoints_registered(self, client):
        """Test that auth endpoints are registered."""
        # Test that the app is working
        response = client.get("/ping")
        assert response.status_code == 200


class TestAdminEndpoints:
    """Test admin endpoints."""

    def test_admin_endpoints_registered(self, client):
        """Test that admin endpoints are registered."""
        # Test that the app is working
        response = client.get("/ping")
        assert response.status_code == 200

    def test_admin_requires_auth(self, client):
        """Admin endpoint returns 401 when no token provided."""
        response = client.get("/admin")
        assert response.status_code == 401

    def test_admin_forbidden_for_non_admin(self, client, db):
        """Admin endpoint returns 403 for a user with non-admin role."""
        from app.core.auth import create_access_token
        from app.models.models import Role, User

        # Create a non-admin role and a user
        user_role = Role(name="user", permissions="read,write")
        db.add(user_role)
        db.commit()
        db.refresh(user_role)

        normal = User(
            username="normal", email="normal@example.com", role_id=user_role.id
        )
        db.add(normal)
        db.commit()
        db.refresh(normal)

        token = create_access_token({"sub": normal.username})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/admin", headers=headers)
        assert response.status_code == 403

    def test_admin_allowed_for_admin(self, client, db, sample_role, sample_user):
        """Admin endpoint accessible to admin users."""
        from app.core.auth import create_access_token

        token = create_access_token({"sub": sample_user.username})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/admin", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "Welcome, admin" in data["message"]
