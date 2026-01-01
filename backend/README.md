# Backend

This is the minimal backend for the enterprise ticketing system using FastAPI.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -e .
   ```

4. To install dev dependencies (optional):
   ```
   pip install -e .[dev]
   ```

## Running the Server

Run the server with auto-reload:
```
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`.

## Testing the Endpoint

Test the ping endpoint:
```
curl http://localhost:8000/ping
```

Or open in browser: `http://localhost:8000/ping`

Expected response: `{"status":"ok"}`

## Migrations and Docker

This project uses Alembic for schema migrations and Docker Compose for local development.

- `backend-migrate` service: runs before the `app` service and ensures migrations are applied.
- `scripts/wait_for_db.py`: waits for Postgres to accept connections.
- `scripts/run_migrations.py`: safe runner used by the migrate service — it will `stamp` existing databases if the schema already exists to avoid DuplicateTable errors, otherwise it runs `alembic upgrade heads`.
- `scripts/verify_db_head.py`: prints the current DB alembic heads and expected heads; exits non-zero when they don't match.
- `entrypoints/start.sh`: used by the app container to wait until migrations are present before starting Uvicorn.

Quick dev workflow:

1. Build and start services (migrations run automatically):
```bash
docker compose up -d --build
```
2. Verify DB is at head:
```bash
docker compose exec app python scripts/verify_db_head.py
```
3. To re-run migrations manually:
```bash
docker compose run --rm backend-migrate
```

Notes:
- The containers read the database URL from `DATABASE_URL` environment variable.
- The migration runner will prefer stamping existing schemas to prevent recreating existing tables; review `backend/scripts/run_migrations.py` if you need explicit control.

## Attachments (new schema)

A new `attachments` table has been added to support file attachments for tickets.

- Model: `backend/app/models/models.py` (`Attachment` model)
- Migration: `backend/alembic/versions/add_attachments_20260102.py`
- Tests: `backend/tests/test_attachments_schema.py`

How to apply the migration locally:

PowerShell:
```powershell
$env:DATABASE_URL = 'postgresql://postgres:YOUR_PASS@HOST:5432/DB_NAME'
cd d:\itdesk\backend
alembic -c alembic.ini upgrade head
```

Run the test suite (includes attachments tests):
```bash
cd backend
pytest
```

The `attachments` table includes a `scanned_status` CHECK constraint and indexes on `ticket_id`, `object_key` (unique), and `scanned_status`.
