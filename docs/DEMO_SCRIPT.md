# Demo walkthrough (≈ 7 minutes)

Setup: `uv run python -m app.seed` (fresh data), backend on :8000, frontend on :3000.

1. **Login (30 s).** Point out the demo personas grouped by organization and role, and the
   "Synthetic data" label. Sign in as **Priya Raman (Owner, TPM)**.
2. **Command Center (90 s).** KPI tiles show definitions and denominators (hover ⓘ). Two projects
   are red. Click **"Why red? (6 rules)"** on *Enterprise Data Platform Migration*: every rule lists
   the records that fired it. "Nothing here is a model's opinion." Note "changes by others since your
   last visit" → opens the filtered activity feed with a last-visit marker.
3. **Evidence drill-down (60 s).** Click the `DPM-32` chip → the work item opens: blocked CDC story
   with Given/When/Then acceptance criteria, its blockers (`DPM-33` firewall change, `DPM-34` perf
   test), what it blocks (Silver order model), and the full audit history.
4. **Timeline (60 s).** Baseline (hollow) vs. forecast (filled) diamonds: Bronze ingestion slipped
   +10 working days. Open the milestone → re-baselining needs a written reason and is audited.
5. **RAID (45 s).** Heat map: `DPM-R1` at P4×I4 = 16 drives the red status; escalation trigger and
   contingency are recorded. Decisions tab: `DPM-D3` is proposed — accept it and see who/when recorded.
6. **Board (45 s).** Drag a TWS card from *To do* to *In progress*: WIP limit badge updates, the
   drawer history shows the move. ⌘K → type "billing accuracy" → jump to `RAG-R1`.
7. **Governance (45 s).** Sign out, sign in as **Elena Morales (Viewer)**: the same data, read-only.
   Sign in as **Noah Kim (Orbital Health Labs)**: Meridian's projects do not exist for this tenant;
   pasting a DPM URL shows "does not exist or you do not have access".
8. **Close (30 s).** Phone width: bottom navigation, cards, drawer. Next phases: AI copilot with
   citations, then governed agents with an approval queue (README roadmap).
