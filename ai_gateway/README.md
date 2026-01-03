# ai-gateway

Lightweight AI gateway service (vertical slice) for POST /ai/summarize.

Run locally with Docker Compose

Prerequisites
- Docker & Docker Compose
- Copy `.env` from project root and configure as needed

Start service:

```bash
cd <repo-root>
docker compose up -d ai-gateway
```

Smoke test (PowerShell):

```powershell
$payload = @{ 
  ticket_id = 'TKT-123'
  title = 'Hello'
  description = 'Desc'
  messages = @(@{ type = 'note'; body = 'Contact me@test.com' })
  metadata = @{ org_unit_id = '42'; sensitivity_level = 'low' }
}
$json = $payload | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri 'http://localhost:8001/ai/summarize' -Method Post -Body $json -ContentType 'application/json' -Headers @{ 'x-org-unit' = '42' }
```

Run tests (local):

```bash
python -m pip install -r ai_gateway/requirements.txt
python -m pytest ai_gateway/tests -q
```

CI
- GitHub Actions workflow at `.github/workflows/ai-gateway-ci.yml` builds the image and runs tests inside the container.

Notes
- Environment var `AI_GATEWAY_DB` is used to connect to the DB; when running via Docker Compose it is wired to `DATABASE_URL` by default.
- `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` control the external LLM integration.
- Production: do NOT store production DB credentials in the repo. Use an external secret store or an env file excluded from source control (example: `.env.prod`).
- DB initialization: by default the service will auto-create the `ai_suggestions` and `audit_events` tables on startup (useful for local dev). For production, set `AI_GATEWAY_INIT_DB=false` and run proper migrations instead of relying on auto-creation.

Production example (deploy):

1. Provide a production-only env file (never commit):

```
# .env.prod (example, DO NOT COMMIT)
AI_GATEWAY_DB=postgresql://<user>:<password>@<host>:5432/<db>
OPENROUTER_API_KEY=<your-key>
AI_GATEWAY_INIT_DB=false
```

2. Start the service using the production compose file (example):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build ai-gateway
```

3. Run migrations against `AI_GATEWAY_DB` before startup, or set `AI_GATEWAY_INIT_DB=true` once to bootstrap (not recommended for managed DBs).

