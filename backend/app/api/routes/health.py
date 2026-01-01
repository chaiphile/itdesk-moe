from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.db.health import check_db

router = APIRouter()


@router.get("/healthz")
def healthz():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/readyz")
def readyz():
    try:
        db_ok = check_db()
        if db_ok:
            return {
                "status": "ready",
                "checks": {"database": "ok"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unavailable",
                    "checks": {"database": "fail"},
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unavailable",
                "checks": {"database": "fail"},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
