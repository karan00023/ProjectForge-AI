# Backlog

Priority: **P0** MVP-blocking · **P1** MVP · **P2** post-MVP.
Status: ✅ done · 🟡 in progress · ⬜ not started. (Updated in `PROGRESS.md` per session.)

## EPIC CORE — PM foundation (Phase 1)

| ID | Story | P | Acceptance criteria | Status |
|---|---|---|---|---|
| CORE-1 | As a user I can sign in with email/password and sign out | P0 | Given valid credentials, a session cookie is set (httpOnly) and `/auth/me` returns me; wrong password → 401 without revealing which field; logout invalidates the session server-side | ✅ |
| CORE-2 | As a demo visitor I can sign in as a synthetic persona in one click | P0 | Only when `DEMO_MODE=true`; personas listed with role; labelled "Demo" in UI | ✅ |
| CORE-3 | As a member of several orgs I only see data of the active org | P0 | Cross-org GET/PATCH/DELETE on every resource returns 404; tested | ✅ |
| CORE-4 | As a viewer I cannot change anything | P0 | All mutating endpoints return 403 for viewer; tested | ✅ |
| CORE-5 | As a PM I can create, edit, archive projects (manually or from a template) | P0 | Key unique per org; methodology (scrum/kanban/waterfall/hybrid); template seeds standard epics & milestones | ✅ |
| CORE-6 | As a PM I can manage a work hierarchy (initiative→epic→feature→story→task/subtask, bug) | P0 | Parent type must be higher in hierarchy; per-project numbering `KEY-n`; soft delete | ✅ |
| CORE-7 | As a PM I can link dependencies between items | P0 | `blocks` links cannot form cycles (409 with the cycle path); self-links rejected; cross-project links within the same org allowed | ✅ |
| CORE-8 | As a PM I can track milestones against a baseline | P0 | Baseline date frozen on creation; re-baseline is an explicit audited action; variance in working days shown | ✅ |
| CORE-9 | As a PM I can maintain a RAID register | P0 | Type-specific fields; risk score = P×I; owner, due, mitigation, escalation trigger, related items | ✅ |
| CORE-10 | As a PM I can log decisions with rationale and alternatives | P0 | Who/when/why recorded; supersede links old→new | ✅ |
| CORE-11 | As anyone I can see an activity feed of what changed | P1 | Driven by audit log; filter by project; "since last login" marker | ✅ |
| CORE-12 | Org timezone and working calendar | P2 | Overdue/variance respect org TZ and holidays | ⬜ |
| CORE-13 | Global search across projects, items, RAID, decisions | P1 | Postgres FTS, tenant-scoped, ranked | ✅ |
| CORE-14 | Sprints: create, commit items, close with spillover | P1 | Closing moves unfinished items to next sprint/backlog and records spillover | 🟡 (create/commit; close+spillover in Phase 4) |
| CORE-15 | Bulk import projects/items from CSV/JSON | P1 | Validation report per row; nothing persisted on any error unless "skip invalid" chosen | ⬜ |

## EPIC DASH — Command center

| ID | Story | P | Acceptance criteria | Status |
|---|---|---|---|---|
| DASH-1 | Portfolio health with explanations | P0 | Each project status lists triggering signals with links to records; no AI-generated numbers | ✅ |
| DASH-2 | KPI tiles (active projects, completed items 14d, on-time milestone rate, open critical risks) | P0 | Each tile shows definition on hover and its denominator | ✅ |
| DASH-3 | Upcoming deadlines, blocked work, critical risks lists | P0 | Drill down to record | ✅ |
| DASH-4 | Customizable dashboard layout | P2 | Show/hide and reorder widgets, persisted per user | ⬜ |
| DASH-5 | Daily PM briefing (Journey 10) | P1 | Changes since last visit, approvals pending, risks, recommended next actions (AI-labelled) | ⬜ |

## EPIC UX — Shell

| ID | Story | P | Acceptance criteria | Status |
|---|---|---|---|---|
| UX-1 | Command palette ⌘K with navigation + search | P1 | Keyboard operable; screen-reader labels | ✅ |
| UX-2 | Dark/light theme | P1 | Persisted; respects system preference | ✅ |
| UX-3 | Kanban board with drag-and-drop and WIP limits | P0 | Status change persisted; WIP limit exceeded shows warning, not a block | ✅ |
| UX-4 | Responsive mobile layout | P1 | 375px: navigation, status review, add update | ✅ |
| UX-5 | Timeline (milestones + dated items, baseline marker) | P1 | Renders from data; today line | ✅ |
| UX-6 | Onboarding wizard for empty org | P2 | | ⬜ |
| UX-7 | Notifications center | P1 | Phase 5 | ⬜ |

## EPIC AI — Copilot (Phase 2)

| ID | Story | P | Acceptance criteria |
|---|---|---|---|
| AI-1 | Provider abstraction (Anthropic, OpenAI, Demo) with usage ledger | P0 | Missing keys ⇒ demo provider + visible badge; every call logged with tokens/cost |
| AI-2 | Budgets per org and per run | P0 | Call refused before execution when budget would be exceeded |
| AI-3 | Project-aware chat with citations | P0 | Answers cite record IDs; refuses to state status not in data |
| AI-4 | Meeting notes → minutes, decisions, actions, stories (review before save) | P0 | Nothing persisted until user accepts; edits allowed per item |
| AI-5 | Story quality: INVEST check, AC generation (Given/When/Then), ambiguity | P1 | Findings tied to text spans |
| AI-6 | Weekly / executive report from stored data | P0 | Sections: done, in progress, blockers, risks, decisions needed, next; missing data flagged; Markdown export |
| AI-7 | Conversational project creation (Journey 1) | P1 | Charter, backlog, roadmap, RAID drafted; user approves before persist |
| AI-8 | Document ingestion + hybrid search | P1 | FTS always; vectors when embeddings configured; tenant-filtered in SQL |
| AI-9 | Decision drift / contradiction detection | P2 | |

## EPIC AGENT — Orchestration (Phase 3)

| ID | Story | P | Acceptance criteria |
|---|---|---|---|
| AGENT-1 | Agent registry with roles, tools, output schemas, budgets | P0 | 12 agents defined; deterministic ones flagged |
| AGENT-2 | Chief PM plans a request as a typed task DAG | P0 | Plan validated; shown before run |
| AGENT-3 | Task queue + worker with retries, cancellation, max budget | P0 | Cancel stops further tasks; failed task retried ≤2 then marked failed |
| AGENT-4 | Proposals and approval queue | P0 | Write tools only create proposals; approve executes via domain services; reject records reason |
| AGENT-5 | Execution trace, tool-call log, cost per run | P0 | Visible in Agent Control Center |
| AGENT-6 | Agent Control Center UI | P0 | Inspect plan, tasks, outputs; approve/reject; stop run |

## EPIC DELIVERY — Intelligence (Phase 4)

| ID | Story | P | Acceptance criteria |
|---|---|---|---|
| DEL-1 | Critical path & slip impact (deterministic) | P0 | Given a slip of N days on node X, returns moved items/milestones with new dates; tested on fixtures |
| DEL-2 | Gantt with baseline vs actual | P1 | |
| DEL-3 | Sprint planning with capacity + realism (Monte Carlo on throughput) | P0 | Shows P50/P85 and assumptions |
| DEL-4 | Velocity, burndown, burnup | P1 | From recorded history only |
| DEL-5 | Release readiness: criteria, go/no-go, AC→test coverage | P0 | Untested AC listed |
| DEL-6 | Data engineering toolkit (sources, pipelines, contracts, DQ, reconciliation) | P0 | Demo A populated |
| DEL-7 | AI evaluation registry linked to release gates | P0 | Gate fails without a persisted passing eval run |
| DEL-8 | Resource capacity & allocation, skills matrix | P1 | |

## EPIC INT — Integrations & automation (Phase 5)

| ID | Story | P | Acceptance criteria |
|---|---|---|---|
| INT-1 | Adapter framework + mock GitHub/Jira | P0 | |
| INT-2 | Real GitHub: link repo, import issues, sync status | P0 | Only after a validated credential; sync log; idempotent |
| INT-3 | Webhooks with dedupe + polling fallback | P1 | |
| INT-4 | Automation engine (schedule/event → agent run/notification) | P1 | History, retries, approval policy |
| INT-5 | Jira live adapter | P2 | |

## EPIC SEC — Security & governance

| ID | Story | P | Status |
|---|---|---|---|
| SEC-1 | Argon2id passwords, hashed session tokens, httpOnly cookies | P0 | ✅ |
| SEC-2 | Login rate limiting | P0 | ✅ (in-process) |
| SEC-3 | PostgreSQL RLS as second isolation layer | P2 | ⬜ |
| SEC-4 | Security headers, CSRF header check | P0 | ✅ |
| SEC-5 | Dependency + secret scanning in CI | P1 | ⬜ (pip-audit/npm audit in CI planned) |
| SEC-6 | Prompt-injection test corpus for AI features | P1 | ⬜ |
| SEC-7 | Sensitive data redaction before LLM calls | P1 | ⬜ |
