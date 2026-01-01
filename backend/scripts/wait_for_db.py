#!/usr/bin/env python3
"""Wait for the database to be available using DATABASE_URL env var."""
import os
import sys
import time

import psycopg2


def wait_for_db(timeout: int = 60) -> int:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2

    # Normalize URI for psycopg2: strip any SQLAlchemy-style driver hint like '+psycopg2'
    if url.startswith("postgresql+"):
        # e.g. 'postgresql+psycopg2://user:pass@host:port/db' -> 'postgresql://user:pass@host:port/db'
        url = url.split("://", 1)[0].split("+", 1)[0] + "://" + url.split("://", 1)[1]

    for i in range(timeout):
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print("database is available")
            return 0
        except Exception:
            print("waiting for database...", flush=True)
            time.sleep(1)

    print("database did not become available in time", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(wait_for_db())
