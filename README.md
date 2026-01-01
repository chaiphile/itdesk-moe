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
