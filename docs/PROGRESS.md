# Progress log

Resume here at the start of each session.

## Current state — 2026-10-28

**Phase 0 ✅ · Phase 1 ✅ · Phase 2 next.** Branch: `claude/keen-fermi-faa58l`.

### Phase 0 — product & architecture (done)
- Three architectures compared; modular monolith chosen (`ARCHITECTURE.md`, ADR-0001…0008).
- MVP boundary, phases with exit criteria (`IMPLEMENTATION_PLAN.md`), backlog with acceptance
  criteria (`BACKLOG.md`), 14 additional capabilities ranked (`PRODUCT_VISION.md`).

### Phase 1 — PM foundation (done)
Exit criteria from the plan, all demonstrated by automated tests (`TEST_RESULTS.md`):
- [x] Demo user logs in and sees honest health for three demo projects
- [x] Create project + items + a risk, reload, persisted
- [x] Viewer cannot write (API 403 on every mutation; UI read-only)
- [x] Another organization cannot read (API 404 on every resource; UI "no access")

Key files:
- Backend: `backend/app/core/{deps,security,audit}.py`, `backend/app/services/health.py`,
  `backend/app/api/*.py`, `backend/app/seed/demo.py`, migration `alembic/versions/20261028_0001_*`.
- Frontend: `frontend/src/app/(app)/**`, `frontend/src/components/**`, `frontend/src/lib/{api,queries}.ts`.

### Deliberate scope decisions in Phase 1
- No component kit (ADR-0007); no SQLite fallback (ADR-0002).
- Sprint management UI, member admin UI and bulk import deferred (see `KNOWN_LIMITATIONS.md`).

## Next milestone — Phase 2: AI copilot

Suggested order (vertical slices, each with demo-mode output, schema validation tests, usage logging):
1. `ai/` module: `LLMProvider` protocol, `DemoProvider`, `AnthropicProvider`; `ai_usage` table
   (model, tokens, cost, latency, purpose); per-org budget check before calls; "Demo AI" badge.
2. **Weekly status report** (Journey 5) from stored data: deterministic fact assembly
   (done / in progress / blocked / risks / decisions needed / missing data), LLM only phrases it;
   every bullet cites record keys; Markdown export.
3. **Meeting notes → actions & stories** (Journey 2) with a review screen; nothing persisted until accepted.
4. **Project-aware chat** with tool calls over the read API (scoped by the caller's role) and citations.
5. Documents + hybrid search (FTS now; pgvector when an embedding provider is configured).

Open questions for the product owner:
- Which model provider should the non-demo path default to, and what monthly AI budget is acceptable for a hosted demo?
- Is a hosted public demo wanted (affects `DEMO_MODE`, rate limits, and reset schedule)?
