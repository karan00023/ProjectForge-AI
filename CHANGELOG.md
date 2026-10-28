# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.

## [0.1.0] — 2026-10-28 — Phase 1: PM foundation

### Added
- Product vision, architecture options and decision records, implementation plan and backlog.
- PostgreSQL schema (Alembic): organizations, users, sessions, memberships, teams, portfolios,
  programs, projects, hierarchical work items, dependency links, sprints, baselined milestones,
  RAID items, decisions, audit events; full-text search columns.
- Session authentication, demo personas, role-based access, tenant isolation, CSRF header check,
  login rate limiting, security headers.
- Project templates; work-item hierarchy rules; cycle-safe dependencies; audited milestone
  re-baselining; decision supersession.
- Rule-based explainable project health and Command Center aggregates; activity feed; global search.
- Next.js UI: Command Center, projects, project overview, board, backlog, timeline, RAID, decisions,
  activity, work-item drawer, command palette, shortcuts, themes, mobile navigation.
- Synthetic demo dataset (three projects + an isolated second tenant).
- 52 backend tests, 11 Playwright tests (including axe accessibility checks), GitHub Actions CI,
  Dockerfiles and Docker Compose.
