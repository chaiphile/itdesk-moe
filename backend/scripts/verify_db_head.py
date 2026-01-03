#!/usr/bin/env python3
"""Verify that the database Alembic revision equals the expected head.

Prints current DB revision and expected head, exits non-zero if they differ.
"""
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory


def find_alembic_ini() -> str:
    # Prefer alembic.ini next to this script's package root (backend/)
    here = Path(__file__).resolve().parent
    candidate = (here.parent / "alembic.ini").resolve()
    if candidate.exists():
        return str(candidate)
    # fall back to cwd
    cwd_candidate = Path(os.getcwd()) / "alembic.ini"
    if cwd_candidate.exists():
        return str(cwd_candidate.resolve())
    raise FileNotFoundError("alembic.ini not found")


def main() -> int:
    try:
        alembic_ini = find_alembic_ini()
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    cfg = Config(alembic_ini)
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()

    # Enforce a single head going forward
    if not heads:
        print("No Alembic heads found", file=sys.stderr)
        return 5
    if len(heads) > 1:
        print(f"ERROR: multiple alembic heads detected: {heads}", file=sys.stderr)
        return 6

    expected = heads[0]

    # Get DB URL from environment via application settings if available
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        # try importing app settings
        try:
            from app.core.config import get_settings

            db_url = get_settings().DATABASE_URL
        except Exception:
            pass

    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 3

    engine = create_engine(db_url)
    with engine.connect() as conn:
        mc = MigrationContext.configure(conn)
        try:
            current_heads = mc.get_current_heads()
        except Exception:
            # older alembic may not have get_current_heads
            current = mc.get_current_revision()
            current_heads = [current] if current else []

    # Simplified, single-head comparison
    db_current = None
    if current_heads:
        # pick first non-None current head if available
        db_current = next((h for h in current_heads if h), None)

    print(f"expected head: {expected}")
    print(f"db current: {db_current}")

    if db_current == expected:
        print("OK: DB is at expected head")
        return 0

    print("ERROR: DB current revision does not match expected head", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())
