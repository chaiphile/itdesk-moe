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

## Scanner & E2E presign flow

This repository includes an attachment scanner that integrates with an on-prem ClamAV daemon and a worker container that scans uploaded attachments and updates their `scanned_status`.

- Service: `attachment-scanner` (defined in top-level `docker-compose.yml`) polls the database for attachments with `scanned_status = 'PENDING'`, downloads the object from MinIO, scans using clamd INSTREAM, and updates `scanned_status` to `CLEAN`, `INFECTED`, or `FAILED`.
- ClamAV: `clamav` service listens on TCP 3310; the scanner connects to `CLAMAV_HOST:CLAMAV_PORT` (defaults `clamav:3310`).

Quick run (local development):

1. Build and start the full stack (app, Postgres, MinIO, ClamAV, scanner):

```powershell
docker compose up -d --build
```

2. Create a live test user and token inside the `app` container (used by the example flow):

```powershell
$env:DATABASE_URL='sqlite:///D:/itdesk/backend/dev_local.db'; python scripts/create_live_user_and_token.py
```

3. Create a ticket (optional helper):

```powershell
python scripts/create_local_ticket.py
```

4. Presign upload and upload a file (example PowerShell snippet):

```powershell
#$token = (docker compose exec -T -e PYTHONPATH=/app app python scripts/create_live_user_and_token.py | Out-String).Trim()
#$body = @{original_filename='sample.pdf'; mime='application/pdf'; size=1234} | ConvertTo-Json
#$presign = Invoke-RestMethod -Uri 'http://localhost:8000/tickets/2/attachments/presign' -Method Post -Body $body -ContentType 'application/json' -Headers @{Authorization="Bearer $token"}
# Note: presigned `upload_url` returned by the API may use the container-internal MinIO host `minio:9000`.
#
# Public presigned URLs
#
# The backend talks to MinIO using an internal endpoint (S3_ENDPOINT, e.g. `http://minio:9000`) so
# services inside Docker can reach the storage. However the presigned PUT/GET URLs returned to
# browser or host clients must use a host reachable from the client. Configure `S3_PUBLIC_BASE_URL`
# with a public base (scheme + host[:port]) that should replace the internal MinIO host in
# returned presigned URLs. Examples:
#
# - Local dev: `S3_PUBLIC_BASE_URL=http://localhost:9000`
# - Production: `S3_PUBLIC_BASE_URL=https://files.myorg.edu`
#
# When `S3_PUBLIC_BASE_URL` is set the API rewrites presigned URLs generated against the internal
# S3 endpoint so the returned URL has the public scheme+netloc while preserving the path and
# query string (do NOT re-encode or reorder query parameters; the signature must remain intact).
```

5. Poll the download presign endpoint until the scanner marks the attachment `CLEAN` and the endpoint returns a `download_url`.

6. Download the file (again rewriting `minio:9000` to `127.0.0.1:9000` when running from the host).

Notes & troubleshooting:
- If `attachment-scanner` fails to import the `app` package, ensure the `PYTHONPATH=/app` environment variable is set for that service in `docker-compose.yml`.
- If presigned URLs include the internal hostname `minio`, either run uploads/downloads from inside the compose network (container) or rewrite the host to your machine's reachable address (e.g. `127.0.0.1`).
- The scanner logs to stdout — use `docker compose logs -f attachment-scanner` to watch scanning progress.

