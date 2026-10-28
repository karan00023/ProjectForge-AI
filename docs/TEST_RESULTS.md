# Test results

Only results from actual executions are recorded here.

## Run of 2026-10-28 (end of Phase 1)

Environment: Linux, Python 3.13.17 (uv 0.11.32), PostgreSQL 16.15, Node 22.22.0, Chromium via
Playwright 1.63.0. Executed locally in the development container; **GitHub Actions has not run yet.**

| Check | Command | Result |
|---|---|---|
| Python lint | `uv run ruff check .` | ✅ pass |
| Python format | `uv run ruff format --check .` | ✅ pass |
| Python types | `uv run mypy app` (strict on `app/core`, `app/services`) | ✅ no issues, 33 files |
| Migration drift | `uv run alembic check` | ✅ no new operations |
| Backend tests | `uv run pytest` | ✅ **52 passed**, 0 failed (≈45 s) |
| Frontend lint | `npm run lint` | ✅ pass |
| Frontend types | `npm run typecheck` | ✅ pass |
| Production build | `npm run build` | ✅ compiled |
| End-to-end | `npx playwright test` | ✅ **11 passed**, 0 failed (≈48 s) |
| Docker Compose | `docker compose up --build` | ⚠️ **not executed** — no Docker daemon in this environment |

### Backend suite (52 tests, real PostgreSQL)

- `test_units.py` (9) — working-day arithmetic incl. weekends and negative spans; path finding and
  cycle detection.
- `test_auth.py` (11) — httpOnly cookie, identical 401 for wrong password vs unknown email, tokens
  stored hashed, logout revokes server-side, expired session rejected, unauthenticated 401s, login
  rate limit (429), CSRF header required, security headers, demo login restricted to demo users and
  demo mode, org switching requires membership.
- `test_authorization.py` (7) — viewer gets 403 on **19 mutating endpoints** and 200 on 11 reads;
  member cannot delete projects; **another tenant gets 404 on all 11 reads and 18 writes**, sees
  nothing in lists/search/activity/dashboard, cannot link to, parent under, or assign people from
  another tenant; member lists scoped.
- `test_domain.py` (14) — project key uniqueness/validation, templates, numbering and hierarchy
  rules, date validation, done → completed_at + audit diff, no-op updates not audited, dependency
  cycles rejected with path, cross-project links, re-parenting on delete, **20 concurrent creates
  from 4 threads get unique sequential numbers**, milestone variance/re-baseline/completion, sprint
  totals, RAID rules and generated score, decision who/when/supersede.
- `test_insights.py` (11) — health rules (green baseline, overdue milestone with evidence, slip
  thresholds 5/10 working days, overdue & blocked items, risk/issue levels, stale data, closed
  projects), dashboard KPIs and since-last-visit count, "—" when no denominator, search (FTS + key
  lookup), activity filters, demo seed coherence and idempotency.

### End-to-end suite (11 tests, Chromium)

1. Command Center explains DPM's red status; evidence chip opens the work item with its 3 ACs.
2. Create project from the data-migration template → backlog item → reload → persisted; timeline shows template milestones.
3. Drag a card To do → In progress; status and audit entry visible in the drawer.
4. Logging a P5×I4 risk turns the project's health red with the risk as evidence.
5. Accepting a proposed decision records "Accepted by Sofia Okafor".
6. Command palette full-text search navigates to `RAG-R1`.
7. Viewer: no create button, read-only board notice, disabled drawer fields.
8. Second tenant cannot see Meridian projects; direct URL shows "no access".
9. axe (WCAG 2.1 A/AA, serious+critical) on login, Command Center and six project screens — dark theme.
10. axe on Command Center and RAID — light theme.
11. Mobile (Pixel 7): bottom navigation, board, drawer, no horizontal overflow.

Issues found by these tests and fixed before this run: project creation navigation overridden by a
URL rewrite; insufficient contrast of accent badges, avatar initials, dimmed done rows and
light-theme warning text.

## Not yet tested

- Docker images and Compose stack; the CI workflow itself.
- Load/performance beyond the 20-request concurrency test.
- Keyboard-only drag-and-drop (not supported; status is changed via the drawer).
- Browsers other than Chromium.
- AI provider failures, agent orchestration, integrations — those features do not exist yet.
