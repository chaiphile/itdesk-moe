from app.core.auth import create_access_token
from app.core.org_unit import create_org_unit
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Ticket, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.storage import get_storage_client

# Setup in-memory SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

db = TestingSessionLocal()

# create org unit
school = create_org_unit(db, name="S", type="school")

# create user
user = User(
    username="testuser", email="t@example.com", role_id=None, org_unit_id=school.id
)
db.add(user)
db.commit()
db.refresh(user)

# create ticket
ticket = Ticket(
    title="T",
    description="d",
    status="OPEN",
    priority="MED",
    created_by=user.id,
    owner_org_unit_id=school.id,
)
db.add(ticket)
db.commit()
db.refresh(ticket)


# override get_db dependency
def override_get_db():
    try:
        yield db
    finally:
        pass


app.dependency_overrides[get_db] = override_get_db

# override storage dependency


class FakeStorageClient:
    def presign_put(self, *, bucket, key, content_type, expires_seconds):
        return "http://example/upload"


app.dependency_overrides[get_storage_client] = lambda: FakeStorageClient()

client = TestClient(app)

# create token
token = create_access_token({"sub": user.username})
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payload = {
    "original_filename": "test.pdf",
    "mime": "application/pdf",
    "size": 12345,
    "checksum": None,
}
resp = client.post(
    f"/tickets/{ticket.id}/attachments/presign", headers=headers, json=payload
)
print("status_code:", resp.status_code)
print(resp.json())

# cleanup
app.dependency_overrides.clear()
