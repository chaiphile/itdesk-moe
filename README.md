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
