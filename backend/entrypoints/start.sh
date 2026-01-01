#!/usr/bin/env sh
set -e

# Wait until DB is at alembic head (verify_db_head.py returns 0)
# Timeout after 120 seconds
TIMEOUT=120
COUNT=0
while [ "$COUNT" -lt "$TIMEOUT" ]; do
  echo "checking alembic head... ($COUNT/$TIMEOUT)"
  if python scripts/verify_db_head.py; then
    echo "migrations present — starting app"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
  fi
  COUNT=$((COUNT+1))
  sleep 1
done

echo "timed out waiting for migrations" >&2
exit 1
