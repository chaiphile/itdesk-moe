#!/usr/bin/env python3
"""Run Alembic migrations safely in containers.

Behavior:
- Wait for DB to be ready
- If `alembic_version` table exists -> run `alembic upgrade heads`
- Else if known tables (e.g. users) exist -> run `alembic stamp heads` (don't recreate)
- Else run `alembic upgrade heads`
"""
import os
import sys

from sqlalchemy import create_engine, text


def wait_for_db(timeout: int = 60) -> None:
    # Run the helper as a subprocess to avoid package/import issues inside containers
    import subprocess

    rc = subprocess.run([sys.executable, "scripts/wait_for_db.py"]).returncode
    if rc != 0:
        print("wait_for_db failed", file=sys.stderr)
        sys.exit(rc)


def main() -> int:
    # ensure env
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        try:
            from app.core.config import get_settings

            db_url = get_settings().DATABASE_URL
        except Exception:
            pass

    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2

    wait_for_db()

    engine = create_engine(db_url)
    with engine.connect() as conn:
        # check alembic_version table
        res = conn.execute(
            text("SELECT to_regclass('public.alembic_version')")
        ).scalar()
        if res:
            print("alembic_version table exists — running upgrade heads")
            rc = os.system("alembic -c alembic.ini upgrade heads")
            return rc

        # if alembic_version missing but tables exist, assume schema already present
        tbl_check = conn.execute(text("SELECT to_regclass('public.users')")).scalar()
        if tbl_check:
            print(
                "Detected existing schema (users table). Stamping alembic heads without running migrations."
            )
            rc = os.system("alembic -c alembic.ini stamp heads")
            return rc

    # default: run migrations
    return os.system("alembic -c alembic.ini upgrade heads")


if __name__ == "__main__":
    sys.exit(main())
