from app.core.config import get_settings
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def ping():
    settings = get_settings()
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}
