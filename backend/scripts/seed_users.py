#!/usr/bin/env python3
"""Script to seed the database with test users."""

from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.models.models import User, Role

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_users():
    """Seed test users."""
    db = SessionLocal()

    try:
        # Get roles
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        user_role = db.query(Role).filter(Role.name == "user").first()

        if not admin_role or not user_role:
            print("Roles not found. Please run seed_roles.py first.")
            return

        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print("Users already exist in the database.")
            return

        # Create test users
        users_data = [
            {"username": "admin", "email": "admin@example.com", "role_id": admin_role.id},
            {"username": "user1", "email": "user1@example.com", "role_id": user_role.id},
            {"username": "user2", "email": "user2@example.com", "role_id": user_role.id},
        ]

        for user_data in users_data:
            user = User(**user_data)
            db.add(user)

        db.commit()
        print("Successfully seeded users:")
        for user_data in users_data:
            print(f"  - {user_data['username']}: {user_data['email']}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
