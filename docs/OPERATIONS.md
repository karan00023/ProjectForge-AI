# Operations

## Configuration

All configuration is environment-based (`backend/app/config.py`; template in `backend/.env.example`).

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local `projectforge` DB | SQLAlchemy URL (`postgresql+psycopg://…`) |
| `DEMO_MODE` | `true` | One-click demo personas. **Disable for real data.** |
| `COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `SESSION_TTL_HOURS` | `168` | Session lifetime |
| `LOGIN_RATE_LIMIT_ATTEMPTS` / `_WINDOW_SECONDS` | `10` / `300` | Per IP + email |
| `API_URL` (frontend, build time) | `http://localhost:8000` | Where Next.js proxies `/api/*` |

## Database migrations

```bash
cd backend
uv run alembic upgrade head        # apply
uv run alembic check               # fails if models and migrations drift
uv run alembic downgrade -1        # roll back one revision
```

## Demo data

```bash
uv run python -m app.seed                 # (re)load, dates anchored to today
uv run python -m app.seed --today 2026-06-15
uv run python -m app.seed --reset-only    # remove demo organizations and users
```

Only organizations/users flagged `is_demo` are touched.

## Backup and restore

The database is the only state. Use standard PostgreSQL tooling:

```bash
pg_dump --format=custom --no-owner "$PGURL" > projectforge-$(date +%F).dump
pg_restore --clean --if-exists --no-owner -d "$PGURL" projectforge-2026-10-28.dump
```

Recommended for a hosted demo: daily dumps retained 14 days, plus the provider's point-in-time
recovery if available. Test a restore into a scratch database at least once per release.

## Data retention

| Data | Policy |
|---|---|
| Sessions | Expired sessions of a user are purged on that user's next login; a scheduled purge job is backlog |
| Audit events | Retained indefinitely (append-only); configurable retention is backlog |
| Soft-deleted records (`deleted_at`) | Hidden from all reads; hard-delete after 90 days is a planned maintenance job |
| Demo data | Replaced on every seed |

## Health check

`GET /api/healthz` → `{"status": "ok"}` (process liveness; does not touch the database).
