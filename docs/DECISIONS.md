# Architecture Decision Records

Short-form ADRs. Each: context → decision → consequences. Superseded ADRs stay
in place with a pointer.

---

## ADR-0001 — Modular monolith: FastAPI backend + Next.js frontend

**Status:** accepted (2026-10-28)

**Context.** A solo developer needs a product that is ambitious (agents, RAG,
scheduling engines, integrations) yet runnable on a laptop and cheap to demo.
Three options were compared in `ARCHITECTURE.md §1`.

**Decision.** One Python/FastAPI backend holds all domain logic, AI, agents and
integrations as internal modules. A Next.js frontend is UI-only and reaches the
API through a same-origin rewrite.

**Consequences.** + one test suite proves authorization and approval rules for
every caller (UI, agents, automations). + Python ecosystem for structured AI
output and numeric engines. − two runtimes to install; mitigated with Docker
Compose and OpenAPI-generated TypeScript types.

---

## ADR-0002 — PostgreSQL as the only stateful dependency

**Status:** accepted

**Decision.** PostgreSQL 16 is the system of record, the job queue
(`FOR UPDATE SKIP LOCKED`), the full-text index (`tsvector`/GIN), the vector store
(pgvector, optional), and the audit log. Tests run against a real PostgreSQL —
no SQLite substitution — so constraints, generated columns and FTS behave as in
production.

**Consequences.** Lowest infra footprint; no Redis/Kafka/vector-DB bill. Throughput
ceiling is far above what a demo or small team needs. If a dedicated queue is ever
required, the queue lives behind one module interface.

---

## ADR-0003 — No mandatory paid services; demo mode without API keys

**Decision.** With no AI keys configured, a `DemoProvider` returns deterministic,
visibly labelled synthetic output so AI journeys can be walked through. All core
PM features (CRUD, health, scheduling, reports built from data) work without any
AI. Real providers are opt-in via env vars and gated by budgets.

---

## ADR-0004 — Tenant isolation in the application layer first, RLS later

**Context.** Multi-tenancy must be safe from day one; Postgres Row-Level Security
is the strongest guard but complicates migrations, connection pooling and tests.

**Decision.** Every tenant table carries `organization_id`; every query is scoped
through request context derived from a verified membership; cross-tenant reads
return 404. Isolation is enforced by tests that try to read/write across orgs for
every resource type. RLS is backlog item `SEC-3` as defence in depth.

---

## ADR-0005 — Agents are configurations on one runtime; deterministic work stays deterministic

**Decision.** An "agent" = role prompt + allowed tools + output schema + model
tier + budget. A single orchestrator executes a typed plan. Specialists whose job
is computation (critical path, capacity, overdue scan, sprint math) are plain
Python and never call an LLM. LLMs are used for planning natural-language
requests, synthesis and drafting. Write tools only create proposals; an approval
record is required to execute one.

**Consequences.** Cheap, testable, explainable; avoids "12 chat calls pretending to
be a team". Agent metrics (latency, tokens, cost, success) are first-class rows.

---

## ADR-0006 — Opaque server-side sessions instead of JWTs

**Decision.** Random 256-bit token in an httpOnly cookie, SHA-256 hash stored in
`user_sessions`. Logout and admin revocation are a row delete; no token ever
reaches frontend JavaScript.

**Consequences.** One DB lookup per request (indexed, negligible). Simpler and
safer than JWT refresh/rotation for a first-party web app.

---

## ADR-0007 — Hand-built UI primitives instead of a component kit

**Context.** The brief suggests shadcn/ui and also asks for a distinctive look.

**Decision.** Phase 1 uses a small set of in-repo, accessible Tailwind primitives
(button, badge, dialog, tabs, table, menu). shadcn's approach (copy components
into the repo) is compatible with this and can be adopted per component later.

**Consequences.** Fewer dependencies and a consistent "Nebula" visual language;
we own accessibility of each primitive (covered by axe checks in e2e).

---

## ADR-0008 — Dates, not datetimes, for planning fields

**Decision.** Planned/due/baseline dates are `DATE`; event timestamps are
`TIMESTAMPTZ` in UTC. "Overdue" is evaluated against the organization's "today"
(UTC for now; org timezone setting is backlog `CORE-12`). The app has an
injectable clock so tests and the demo dataset are reproducible.
