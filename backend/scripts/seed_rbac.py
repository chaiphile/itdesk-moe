#!/usr/bin/env python3
"""Script to seed roles and users (RBAC) together."""

from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.models.models import Role, User
from app.core.auth import get_password_hash

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_roles(db):
    """Seed default roles if they don't exist."""
    try:
        existing_roles = db.query(Role).count()
        if existing_roles > 0:
            print("Roles already exist in the database.")
            return False

        roles_data = [
            {"name": "admin", "permissions": "read,write,delete,admin"},
            {"name": "user", "permissions": "read,write"},
            {"name": "viewer", "permissions": "read"},
        ]

        for role_data in roles_data:
            role = Role(**role_data)
            db.add(role)

        db.commit()
        print("Successfully seeded roles:")
        for role_data in roles_data:
            print(f"  - {role_data['name']}: {role_data['permissions']}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error seeding roles: {e}")
        return False


def seed_users(db):
    """Seed a few test users if they don't exist."""
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        user_role = db.query(Role).filter(Role.name == "user").first()
        viewer_role = db.query(Role).filter(Role.name == "viewer").first()

        if not admin_role or not user_role or not viewer_role:
            print("Roles not found. Please run role seeding first.")
            return False

        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Users already exist in the database.")
            return False

        users_data = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "admin123",
                "role_id": admin_role.id
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": "user123",
                "role_id": user_role.id
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "user456",
                "role_id": user_role.id
            },
            {
                "username": "viewer",
                "email": "viewer@example.com",
                "password": "viewer789",
                "role_id": viewer_role.id
            },
        ]

        for user_data in users_data:
            password = user_data.pop("password")
            user = User(**user_data, hashed_password=get_password_hash(password))
            db.add(user)

        db.commit()
        print("Successfully seeded users:")
        for user_data in users_data:
            print(f"  - {user_data['username']}: {user_data['email']}")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error seeding users: {e}")
        return False


def seed_rbac():
    """Run both role and user seeding."""
    db = SessionLocal()
    try:
        print("Seeding roles...")
        roles_seeded = seed_roles(db)
        # Refresh to ensure roles are visible for users
        db.commit()

        print("Seeding users...")
        users_seeded = seed_users(db)

        if roles_seeded or users_seeded:
            print("\n=== RBAC Seeding Finished Successfully ===")
            print("\nTest Credentials:")
            print("  Admin User:")
            print("    username: admin")
            print("    password: admin123")
            print("    role: admin (permissions: read,write,delete,admin)")
            print("\n  Regular User:")
            print("    username: user1")
            print("    password: user123")
            print("    role: user (permissions: read,write)")
            print("\n  Viewer User:")
            print("    username: viewer")
            print("    password: viewer789")
            print("    role: viewer (permissions: read)")
        else:
            print("No changes made during RBAC seeding (already present).")
    except Exception as e:
        print(f"Error during RBAC seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_rbac()
