# ProjectForge AI — Product Vision

## One line

An AI-native project management operating system that runs the *administrative,
analytical and preparation work* of delivery through specialised agents, while
humans keep judgment, approval and accountability.

## The problem

PM tools are systems of record: they store what people type. The expensive work —
noticing that a slipped CDC feed now threatens a launch, turning a 60-minute
meeting into stories with acceptance criteria, writing the Friday status report,
checking that every acceptance criterion has a test before go/no-go — is still done
by hand, late, and inconsistently.

## Who it is for

Technical program managers, product managers/owners, scrum masters, engineering
managers, BAs, data and AI/ML delivery leads, QA leads, portfolio executives — and
solo founders running several initiatives. Strongest fit: **technical delivery**
(data platforms, cloud migrations, AI products), where dependencies and governance
gates are dense and generic tools are weakest.

## Three operating modes

| Mode | Human does | AI does |
|---|---|---|
| A — Manual | Everything | Nothing (AI is fully optional) |
| B — Assisted | Decides and edits | Drafts, critiques, detects gaps, explains |
| C — Agentic | Delegates, reviews, approves | Plans, investigates, prepares changes; executes only approved writes |

## Principles

1. **Never fabricate status.** Every number traces to records; every generated
   claim is labelled source fact / assumption / AI interpretation / recommendation.
2. **Deterministic where possible.** Health, critical path, capacity and forecasts
   are computed; LLMs explain them.
3. **Human approval for consequence.** No deletes, external messages, publication
   or production changes without an explicit approval.
4. **Runs on a laptop.** PostgreSQL only; demo mode with no API keys.
5. **Vertical slices over feature count.** A journey is done when it works end
   to end and is tested.

## Differentiators

- **Data & AI delivery toolkit:** source inventory, CDC dependency maps, data
  contracts, DQ rules, reconciliation; AI evaluation registry linked to release gates.
- **Explainable health:** red/amber/green with the exact records that caused it.
- **Deterministic impact analysis:** "if X slips 2 weeks, what moves?" answered by
  graph computation, explained by AI.
- **Governed agents:** budgets, traces, approvals, audit — inspectable in an Agent
  Control Center.

## Additional capabilities identified (beyond the brief), ranked

Scored 1–5 (higher is better; for complexity and cost, higher = cheaper/easier).

| # | Capability | Value | Differentiation | Ease | Feasibility | Demo value | Cost | Total | Call |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 1 | **Schedule impact simulator** (what-if slip on any node, deterministic CPM) | 5 | 4 | 4 | 5 | 5 | 5 | 28 | **Build now** (Phase 4, engine early) |
| 2 | **Evidence-linked health signals** (every RAG status clickable to its cause) | 5 | 4 | 4 | 5 | 5 | 5 | 28 | **Built in Phase 1** |
| 3 | **"Since you were last here" briefing** from the audit log | 4 | 3 | 5 | 5 | 5 | 5 | 27 | **Build now** (Phase 1–2) |
| 4 | **Commitment realism check** (sprint plan vs. historical throughput, Monte Carlo) | 5 | 4 | 3 | 5 | 5 | 5 | 27 | Phase 4 |
| 5 | **Decision drift detection** (new notes/requirements contradicting logged decisions) | 5 | 5 | 2 | 4 | 5 | 3 | 24 | Phase 2–3 |
| 6 | **Acceptance-criteria-to-test coverage gate** blocking go/no-go | 4 | 4 | 3 | 5 | 4 | 5 | 25 | Phase 4 |
| 7 | **AI eval → release gate linkage** (no model ships without persisted eval run) | 4 | 5 | 3 | 5 | 5 | 4 | 26 | Phase 4 |
| 8 | **Data-contract break radar** (schema change → affected pipelines/reports) | 4 | 5 | 3 | 4 | 5 | 5 | 26 | Phase 4 |
| 9 | **Agent cost ledger + budgets per org/run** | 4 | 3 | 4 | 5 | 4 | 5 | 25 | Phase 3 |
| 10 | **Backlog quality monitor** (INVEST/ambiguity drift over time) | 4 | 3 | 3 | 4 | 4 | 3 | 21 | Phase 2–4 |
| 11 | **Natural-language portfolio query** compiled to safe, scoped SQL views | 4 | 3 | 2 | 3 | 5 | 3 | 20 | Roadmap |
| 12 | **Cross-project lessons retrieval** (retro insights surfaced in planning) | 3 | 4 | 3 | 4 | 3 | 3 | 20 | Roadmap |
| 13 | **Escalation recommender** (who, when, with what evidence) | 3 | 3 | 3 | 4 | 3 | 4 | 20 | Roadmap |
| 14 | **Delivery simulation of staffing scenarios** | 4 | 4 | 2 | 3 | 4 | 4 | 21 | Roadmap |

Challenges to the brief worth stating plainly:

- Twelve agents are a *catalogue*, not a requirement to call twelve models. Most
  value comes from 3–4 well-instrumented agents plus deterministic specialists.
- "Every integration" is a trap for a solo build: one real (GitHub) + one mock PM
  tool demonstrates the framework; more adapters are incremental.
- PDF/Office export: Markdown + print-to-PDF stylesheet first; DOCX later.
