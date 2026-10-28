# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately via GitHub's **"Report a vulnerability"** (Security
Advisories) on this repository rather than in a public issue. Include steps to reproduce and the
affected version/commit. You can expect an acknowledgement within 5 working days.

## Scope and current posture (Phase 1)

| Control | Status |
|---|---|
| Passwords hashed with argon2id; unknown-email logins take the same path as wrong passwords | ✅ |
| Opaque 256-bit session tokens, stored only as SHA-256 hashes; httpOnly, SameSite=Lax cookies; server-side revocation on logout; expiry | ✅ |
| CSRF defence in depth: mutating requests require `X-Requested-With` (no CORS is granted) | ✅ |
| Tenant isolation on every query; cross-tenant ids return 404; tested for every resource type | ✅ |
| Role checks on every mutating endpoint; tested | ✅ |
| Input validation via Pydantic schemas (`extra="forbid"` on writes), DB CHECK constraints | ✅ |
| Login rate limiting | ✅ in-process (single instance only) |
| Security headers (nosniff, frame deny, referrer policy, no-store on API) | ✅ |
| Append-only audit log of every mutation | ✅ |
| Dependency audit in CI (`pip-audit`, `npm audit`) | 🟡 runs, reports as warnings |
| PostgreSQL Row-Level Security as a second isolation layer | ⬜ backlog SEC-3 |
| Prompt-injection defences, redaction, tool allow-lists, approval-gated agent writes | ⬜ designed for Phases 2–3 |
| `Secure` cookies | Set `COOKIE_SECURE=true` behind HTTPS |

## Rules for this repository

- Never commit secrets. Only `.env.example` files are tracked; `.env*` is git-ignored.
- The application must work with synthetic data only; do not load confidential employer or client data.
- `DEMO_MODE=true` exposes one-click sign-in as demo personas and must be disabled on any
  deployment that holds real data.
