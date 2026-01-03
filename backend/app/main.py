from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import Base, engine
from fastapi import FastAPI

settings = get_settings()
app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router)


@app.on_event("startup")
def create_tables():
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
