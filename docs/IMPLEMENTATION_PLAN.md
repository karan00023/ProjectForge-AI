# Implementation Plan

Phases deliver vertical, runnable slices. A phase is "done" only when its exit
criteria are demonstrated and recorded in `TEST_RESULTS.md`.

## MVP boundary (portfolio release)

**In the MVP:** Phases 1–4 core + GitHub integration (Phase 5 subset) + Phase 6
polish. Concretely: auth/tenancy/RBAC, projects + hierarchy + dependencies,
RAID + decisions, explainable health, command center, board/backlog/timeline,
AI copilot (demo + real provider), meeting → stories with review, grounded
weekly report, Chief PM agent with 3–4 specialists and an approval queue,
schedule impact engine, sprint planning with realism check, release readiness
with AI eval gate, GitHub issue sync, three demo projects.

**After the MVP (target architecture):** remaining adapters (Jira live, ADO,
Linear, Slack/Teams, calendars, Confluence/Notion/Drive), automation builder
UI beyond presets, budgets/financial forecasting depth, PWA/offline, RLS,
SSO/SAML, org timezone & calendars, DOCX/PPTX export, NL portfolio query.

## Phases and exit criteria

### Phase 0 — Product & architecture ✅
Docs in `docs/`, ADRs, repo skeleton, data model.

### Phase 1 — Functioning PM foundation
- Backend: schema + migration, session auth, demo login, org/role RBAC,
  projects, hierarchy work items, dependency links (cycle-safe), milestones with
  baselines, sprints, RAID, decisions, audit log, activity feed, global search,
  explainable health, dashboard aggregate, seed with 3 demo projects.
- Frontend: login, command center, projects list/create, project workspace with
  overview / board (drag-and-drop status, WIP limits) / backlog tree / timeline /
  RAID / decisions / activity, command palette, themes, responsive.
- Tests: pytest (unit + API + DB + authz + tenant isolation), Playwright smoke.
- **Exit:** a reviewer logs in as a demo user, sees honest health for 3 demo
  projects, creates a project + items + a risk, reloads, sees them persisted;
  a viewer cannot write; another org cannot read.

### Phase 2 — AI copilot
Provider abstraction (Anthropic, OpenAI, Demo), usage ledger, budgets;
project-aware chat with citations; meeting notes → reviewed actions/stories;
story refinement & INVEST checks; weekly/executive report from stored data with
missing-data flags; document upload + FTS (+ pgvector when embeddings configured).
**Exit:** Journeys 1, 2, 5 work in demo mode and with a real key.

### Phase 3 — Multi-agent system
Agent registry, runs/tasks/tool-calls tables, Postgres task queue worker,
Chief PM planner, deterministic specialists (risk scan, schedule impact,
capacity), LLM specialists (reporting, BA), proposals + approval queue,
cancellation, budgets, traces, Agent Control Center UI.
**Exit:** Journey 6 executes a real multi-step run; write actions wait for
approval; audit shows actor=agent, approved_by=user.

### Phase 4 — Delivery intelligence
CPM/critical path + slip impact, Gantt with baseline vs actual, sprint planning
with capacity & Monte Carlo realism, velocity/burndown, release readiness
(criteria, go/no-go, AC→test coverage), data-engineering toolkit (sources,
pipelines, contracts, DQ rules, reconciliation), AI eval registry → release gate.
**Exit:** Journeys 3, 4, 7, 8.

### Phase 5 — Integrations & automations
Adapter framework, mock GitHub/Jira, real GitHub (PAT/App), sync log, idempotent
mappings, webhook + polling; automation engine with schedule/event triggers,
history, retries, approval policies; notifications.
**Exit:** Journey 9 against a real repository the owner authorizes; Journey 10.

### Phase 6 — Portfolio quality
UX polish, a11y audit, security hardening (rate limits, headers, dependency
scan, secret scan), CI/CD, screenshots of real screens, demo script, deploy guide.

## Engineering standards

- Python: ruff (lint+format), mypy (strict on `app/services`, `app/core`),
  pytest. Frontend: TypeScript strict, ESLint, Prettier defaults, Playwright.
- Conventional, incremental commits; each commit leaves the app runnable.
- No secrets in repo; `.env.example` only. Config from env via pydantic-settings.
- Every new table: migration, model, schema, authz test, tenant-isolation test.
- Every AI feature: works in demo mode, has a validation test for its output
  schema, logs usage, and labels provenance in the UI.
