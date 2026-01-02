itdesk — Quick start and developer notes

## Quick start

1. Copy the example env file:
   - macOS / Linux: `cp .env.example .env`
   - Windows PowerShell: `copy .env.example .env`
2. Edit `.env` and set a secure `POSTGRES_PASSWORD` and `MINIO` credentials.
3. Start the stack (build first run):

```bash
docker compose up -d --build
```

4. Run migrations (containerized):

```bash
docker compose run --rm backend-migrate python scripts/run_migrations.py
```

5. Run the test suite (same behavior as CI):

```bash
docker compose run --rm app_test pytest -q
```

6. To recreate a fresh DB (warning: destroys local volumes):

```bash
docker compose down -v
docker compose up -d --build
```

## Useful validation & troubleshooting

- Ensure no plaintext secrets remain (example):

```bash
grep -R "a98319831a" . || echo "no matches"
# PowerShell
Select-String -Path * -Pattern 'a98319831a' -SimpleMatch -List || Write-Output "no matches"
```

- Verify migrations applied (example):

```bash
docker compose run --rm -e DATABASE_URL=postgresql://postgres:<your_password>@postgres:5432/ticketing_db backend-migrate python scripts/run_migrations.py
```

## MinIO & presign flow (upload + download)

1. Start MinIO services only (if you don't want the full stack):

```bash
docker compose up -d minio minio-mc
```

2. Bring up the app and apply migrations:

```bash
docker compose up -d --build
docker compose run --rm backend-migrate python scripts/run_migrations.py
```

3. Generate a test JWT (inside `app` container or host Python env):

```bash
python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'<username>'}))"
```

4. Create test data using `psql`:

```bash
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO org_units (parent_id,type,name,path,depth) VALUES (NULL,'school','LocalSchool','/00000001',1) ON CONFLICT (name) DO NOTHING;"
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO users (username,name,email,role_id) SELECT 'live_test_user','Live Tester','live@local',(SELECT id FROM roles WHERE name='tester') WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='live_test_user');"
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO tickets (title,description,status,priority,user_id,owner_org_unit_id) SELECT 'Live T','desc','OPEN','MED',(SELECT id FROM users WHERE username='live_test_user'),(SELECT id FROM org_units WHERE name='LocalSchool') WHERE NOT EXISTS (SELECT 1 FROM tickets WHERE title='Live T');"
```

5. Call the presign upload endpoint (replace `YOUR_TOKEN` and ticket id):

```bash
curl -X POST "http://localhost:8000/tickets/1/attachments/presign" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"original_filename":"test.pdf","mime":"application/pdf","size":12345,"checksum":null}'
```

This returns JSON with `attachment_id`, `object_key`, `upload_url`, and `expires_in`. The `upload_url` is a presigned PUT URL for MinIO.

### End-to-end presign helper

A convenience PowerShell script is provided at `backend/scripts/run_e2e_presign.ps1` to perform a full presign PUT upload and presign GET download against a running Docker stack:

```powershell
powershell -ExecutionPolicy Bypass -File backend/scripts/run_e2e_presign.ps1
```

Notes:
- The script assumes the Compose services `postgres`, `minio`, `minio-mc`, and `app` are running.
- If presigned URLs include the internal hostname `minio`, either run uploads/downloads from inside the compose network (container) or rewrite the host to `127.0.0.1` when running from the host.

## Scanner & attachment flow

The `attachment-scanner` service polls the DB for attachments with `scanned_status = 'PENDING'`, downloads objects from MinIO, scans with ClamAV, and updates `scanned_status` to `CLEAN`, `INFECTED`, or `FAILED`.

- ClamAV exposes TCP port `3310` and the scanner uses `CLAMAV_HOST:CLAMAV_PORT` (defaults `clamav:3310`).
- Watch scanner logs with: `docker compose logs -f attachment-scanner`.

## Running tests

- Run the unit/integration test suite from host (one-off container):

```bash
docker compose run --rm app_test pytest -q
```

- Or run only the app tests with Docker Compose up (useful for CI-like behavior):

```bash
docker compose up --build --abort-on-container-exit app_test
```

## Troubleshooting

- If `attachment-scanner` fails to import the `app` package, ensure the service has `PYTHONPATH=/app` in `docker-compose.yml`.
- If you need to inspect the DB or run project scripts inside the app image, use:

```bash
docker compose run --rm app bash
```

---

If you want, I can also:
- Update `backend/README.md` with a short developer Quick Start.
- Run a spellcheck or markdown linter across all `.md` files and propose fixes.
Quick start

- Copy the example env file:
	- macOS / Linux: `cp .env.example .env`
	- Windows PowerShell: `copy .env.example .env`
- Edit `.env` and set a secure `POSTGRES_PASSWORD`.
- Start the stack:

```bash
docker compose up -d --build
```

Run migrations (containerized):

```bash
docker compose run --rm backend-migrate python scripts/run_migrations.py
```

Run the test service (same as CI):

```bash
docker compose up --build --abort-on-container-exit app_test
```

Fresh DB (discard local data):

```bash
docker compose down -v
docker compose up -d --build
```

Validation (before merging):

- Ensure no plaintext secrets remain:

```bash
grep -R "a98319831a" . || echo "no matches"
# PowerShell
Select-String -Path * -Pattern 'a98319831a' -SimpleMatch -List || Write-Output "no matches"
```

- Verify migrations applied (example):

```bash
docker compose run --rm -e DATABASE_URL=postgresql://postgres:<your_password>@postgres:5432/ticketing_db backend-migrate python scripts/run_migrations.py
```

Notes
- `backend/.env` is now ignored and untracked to prevent committing secrets — keep local secrets in `./.env` only.
- If plaintext DB credentials were previously committed, rotate those credentials in your DB and any services; this repo change does not rewrite history.
- CI uses job-level env vars and constructs `DATABASE_URL` at runtime; no secrets are committed in workflows.

**MinIO & Presign Test**
- **Start MinIO:** ensure you have a local `.env` (copy from `.env.example`) then run:

```bash
docker compose up -d minio minio-mc
```

- **Bring up the app and migrations:**

```bash
docker compose up -d --build
docker compose run --rm backend-migrate python scripts/run_migrations.py
```

- **Generate a test JWT:** inside the `app` container (or from your host with the same Python environment) run:

```bash
python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'<username>'}))"
```

- **Create a ticket** (example using `psql` against the `postgres` container):

```bash
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO org_units (parent_id,type,name,path,depth) VALUES (NULL,'school','LocalSchool','/00000001',1) ON CONFLICT (name) DO NOTHING;"
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO users (username,name,email,role_id) SELECT 'live_test_user','Live Tester','live@local',(SELECT id FROM roles WHERE name='tester') WHERE NOT EXISTS (SELECT 1 FROM users WHERE username='live_test_user');"
docker compose exec -T postgres psql -U postgres -d ticketing_db -c "INSERT INTO tickets (title,description,status,priority,user_id,owner_org_unit_id) SELECT 'Live T','desc','OPEN','MED',(SELECT id FROM users WHERE username='live_test_user'),(SELECT id FROM org_units WHERE name='LocalSchool') WHERE NOT EXISTS (SELECT 1 FROM tickets WHERE title='Live T');"
```

- **Call the presign endpoint:** replace `YOUR_TOKEN` with the JWT from above and the ticket id with a real ticket id:

```bash
curl -X POST "http://localhost:8000/tickets/1/attachments/presign" \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer YOUR_TOKEN" \
	-d '{"original_filename":"test.pdf","mime":"application/pdf","size":12345,"checksum":null}'
```

This will return a JSON object containing `attachment_id`, `object_key`, `upload_url`, and `expires_in`. The `upload_url` is a presigned PUT URL pointing at the S3-compatible MinIO endpoint.

End-to-end upload + download (PowerShell)
 - A convenience PowerShell script is provided at `backend/scripts/run_e2e_presign.ps1` to perform a full presign PUT upload and presign GET download against a running Docker stack.
 - From the repository root (Windows PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File backend/scripts/run_e2e_presign.ps1
```

What the script does:
 - Creates a small sample file (`sample.pdf`) in the repo root
 - Generates a JWT for `live_test_user` inside the `app` container
 - Calls the presign upload endpoint to obtain a presigned PUT URL
 - Uploads `sample.pdf` to MinIO using the presigned URL
 - Marks the attachment as `CLEAN` in Postgres (so it can be downloaded)
 - Calls the presign download endpoint and downloads the object to `downloaded.pdf`

If you prefer to run steps manually, use the curl/psql snippets in the previous section to:
 - create the test `org_unit`, `role`, `user`, and `ticket` in Postgres
 - call the presign upload endpoint to get the `upload_url`
 - PUT the file to the `upload_url`
 - update `attachments.scanned_status` to `CLEAN`
 - call the download endpoint to obtain the `download_url` and GET the object

Notes
 - The script assumes Docker Compose services are running (`postgres`, `minio`, `minio-mc`, and `app`).
 - If you run the upload from the host you may need to adjust the presigned URLs (MinIO service host vs container host) depending on your Docker networking.

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
$env:DATABASE_URL='sqlite:///D:/itdesk/backend/dev_local.db'; python backend/scripts/create_live_user_and_token.py
```

3. Create a ticket (optional helper):

```powershell
python backend/scripts/create_local_ticket.py
```

4. Presign upload and upload a file (example PowerShell snippet):

```powershell
#$token = (docker compose exec -T -e PYTHONPATH=/app app python backend/scripts/create_live_user_and_token.py | Out-String).Trim()
#$body = @{original_filename='sample.pdf'; mime='application/pdf'; size=1234} | ConvertTo-Json
#$presign = Invoke-RestMethod -Uri 'http://localhost:8000/tickets/2/attachments/presign' -Method Post -Body $body -ContentType 'application/json' -Headers @{Authorization="Bearer $token"}
# Note: presigned `upload_url` returned by the API may use the container-internal MinIO host `minio:9000`.
# When running the upload from the host, replace `minio:9000` with `127.0.0.1:9000` in the URL before PUTting the file.
```

5. Poll the download presign endpoint until the scanner marks the attachment `CLEAN` and the endpoint returns a `download_url`.

6. Download the file (again rewriting `minio:9000` to `127.0.0.1:9000` when running from the host).

Notes & troubleshooting:
- If `attachment-scanner` fails to import the `app` package, ensure the `PYTHONPATH=/app` environment variable is set for that service in `docker-compose.yml`.
- If presigned URLs include the internal hostname `minio`, either run uploads/downloads from inside the compose network (container) or rewrite the host to your machine's reachable address (e.g. `127.0.0.1`).
- The scanner logs to stdout — use `docker compose logs -f attachment-scanner` to watch scanning progress.

