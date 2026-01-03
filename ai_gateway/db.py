from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

BASE_DIR = os.path.dirname(__file__)
# If AI_GATEWAY_DB is provided prefer it (e.g. a postgresql:// URL). Otherwise fall back to a local sqlite file.
AI_GATEWAY_DB = os.getenv("AI_GATEWAY_DB")
if AI_GATEWAY_DB:
    ENGINE = create_engine(AI_GATEWAY_DB)
else:
    DB_PATH = os.path.join(BASE_DIR, "ai_gateway.db")
    ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=ENGINE)
Base = declarative_base()


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, index=True)
    kind = Column(String, index=True)
    payload_json = Column(JSON)
    model_version = Column(String)
    accepted = Column(Boolean, nullable=True)
    rejected = Column(Boolean, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    feedback_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)
    ticket_id = Column(String, index=True)
    payload_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=ENGINE)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
