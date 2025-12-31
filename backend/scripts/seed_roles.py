#!/usr/bin/env python3
"""Script to seed the database with default roles."""

from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.models.models import Role

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_roles():
    """Seed default roles."""
    db = SessionLocal()

    try:
        # Check if roles already exist
        existing_roles = db.query(Role).count()
        if existing_roles > 0:
            print("Roles already exist in the database.")
            return

        # Create default roles
        roles_data = [
            {"name": "admin", "permissions": "read,write,delete,admin"},
            {"name": "user", "permissions": "read,write"},
        ]

        for role_data in roles_data:
            role = Role(**role_data)
            db.add(role)

        db.commit()
        print("Successfully seeded roles:")
        for role_data in roles_data:
            print(f"  - {role_data['name']}: {role_data['permissions']}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding roles: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles()
