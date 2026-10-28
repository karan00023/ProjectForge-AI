# Known limitations (as of Phase 1, 2026-10-28)

## Not built yet (roadmap, not defects)

- **No AI features.** No LLM provider, chat, story generation, meeting intelligence, reports, RAG,
  or agents exist yet (Phases 2–3). Nothing in the app calls a model.
- No critical-path / slip-impact engine, sprint forecasting, burndown/velocity charts, release
  readiness, resource/financial planning, data-engineering or AI-evaluation toolkits (Phase 4).
- No integrations (GitHub/Jira), automations, or notifications (Phase 5).
- No CSV/JSON bulk import, document upload, or report export.
- Sprint closing with automatic spillover is not implemented (sprints can be created/edited only
  through the API; there is no sprint management UI yet).
- No member/organization administration UI (invites, role changes); users are created by the seed.
- No customizable dashboard layout or onboarding wizard.

## Known gaps in what is built

- **Docker images and Compose are not verified.** This build environment had no Docker daemon, so
  `docker compose up` has not been run. The native setup in the README is verified.
- **CI workflow has not run yet** on GitHub; it mirrors the commands that were run locally.
- Login rate limiting is in-process: correct for one backend instance, not shared across replicas.
- "Today" for overdue/variance is UTC; organization time zones and holiday calendars are not modelled
  (working days are Mon–Fri).
- Tenant isolation is enforced in application code and tests; PostgreSQL Row-Level Security is not
  yet enabled as a second layer.
- Board drag-and-drop uses HTML5 DnD (pointer only). Keyboard users change status via the work-item
  drawer; touch devices also use the drawer.
- RAID "related work items" uses a native multi-select (works, but clunky).
- Dependency cycle checks load all `blocks` edges of the organization in memory — fine for
  thousands of links, would need a recursive SQL query at larger scale.
- Health rules are fixed in code (`rules_version` is reported); per-organization thresholds are
  not configurable.
- Timeline shows only items with dates; very long programs at "week" zoom produce wide charts.
- Expired sessions are purged per user on login; there is no global scheduled cleanup job.
- The frontend has no unit-test layer; behaviour is covered by Playwright end-to-end tests.
