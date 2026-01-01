Quick start

- Copy the example env file: `cp .env.example .env` (Windows: `copy .env.example .env`).
- Edit `.env` and set a secure `POSTGRES_PASSWORD`.
- Run the stack: `docker compose up -d --build`.

If you previously committed plaintext credentials to this repository, rotate those credentials immediately.
