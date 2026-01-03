from app.core.auth import create_access_token
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models.models import Role, User
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

settings = get_settings()

# create tables if missing
Base.metadata.create_all(bind=engine)

session = SessionLocal()
try:
    username = "live_test_user"
    user = session.query(User).filter(User.username == username).first()
    if not user:
        # ensure a role exists
        role = session.query(Role).filter(Role.name == "tester").first()
        if not role:
            role = Role(name="tester", permissions="CONFIDENTIAL_VIEW")
            session.add(role)
            session.commit()
            session.refresh(role)
        user = User(username=username, email="live@local", role_id=role.id)
        session.add(user)
        session.commit()
        session.refresh(user)
    token = create_access_token({"sub": user.username})
    print(token)
finally:
    session.close()
