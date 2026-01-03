#!/bin/sh
set -euo pipefail

# Run Alembic migrations for ai-gateway before starting the app
echo "===> Running alembic upgrade head for ai-gateway"
alembic -c ai_gateway/alembic.ini upgrade head

echo "===> Alembic upgrade completed"

# If command arguments are provided, run them; otherwise start uvicorn
if [ "$#" -gt 0 ]; then
  exec "$@"
else
  exec uvicorn ai_gateway.main:app --host 0.0.0.0 --port 8000
fi
