# Contributing

## Workflow

1. Read `docs/PROGRESS.md` and `docs/BACKLOG.md` to see where things stand.
2. Branch from `main`, keep commits small and descriptive, and keep the app runnable at every commit.
3. Before opening a PR, run the same checks as CI:

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm run build && npx playwright test
```

4. Update `docs/PROGRESS.md`, `docs/TEST_RESULTS.md` and, if behaviour changed, `CHANGELOG.md`.

## Engineering standards

- **Schema changes only via Alembic.** Generate with `uv run alembic revision --autogenerate -m "…"`,
  review the file, and make sure `uv run alembic check` reports no drift.
- **Every tenant-scoped table** carries `organization_id`; every query filters on it via the request
  context (`app/core/deps.py`), and every new resource gets authorization + tenant-isolation tests.
- **Every mutation writes an audit event** in the same transaction (`app/core/audit.py`).
- **Deterministic first:** numbers shown as facts are computed in code with unit tests, never by an LLM.
- **API contract:** after changing schemas, regenerate frontend types with `npm run gen:api`
  (backend running on :8000) and commit `src/lib/api-types.ts`.
- **UI:** no decorative controls — every button must do something; check axe passes in both themes.
- **Honesty:** don't mark features or tests as done in docs without evidence from a real run.
