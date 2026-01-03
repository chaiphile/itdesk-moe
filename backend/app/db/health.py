from app.core.config import get_settings
from sqlalchemy import create_engine, text


def check_db() -> bool:
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if not db_url:
        return False

    try:
        # Create engine with connection pooling disabled for health check
        engine = create_engine(
            db_url, pool_pre_ping=True, connect_args={"connect_timeout": 2}
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
