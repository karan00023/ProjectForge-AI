"""Synthetic demo dataset. Every organization, person, figure and system named here is fictional.

Three projects in "Meridian Freight Co." exercise the product end to end:

* DPM — Enterprise Data Platform Migration (CDC → Bronze/Silver/Gold → Power BI)
* RAG — AI Customer Support Assistant (retrieval-augmented, evaluation-gated)
* TWS — Team Workspaces (SaaS feature delivered over several Scrum sprints)

A second organization, "Orbital Health Labs", exists so tenant isolation can be demonstrated.
"""

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Organization, User
from app.models.enums import (
    DecisionStatus,
    LifecyclePhase,
    Methodology,
    Priority,
    ProjectKind,
    ProjectStatus,
    RaidStatus,
    RaidType,
    Role,
    SprintStatus,
)
from app.models.enums import WorkItemStatus as S
from app.models.enums import WorkItemType as T
from app.seed.builder import Seeder

P = Priority


def reset_demo(db: Session) -> None:
    db.execute(delete(Organization).where(Organization.is_demo.is_(True)))
    db.execute(delete(User).where(User.is_demo.is_(True)))
    db.flush()


def seed_demo(db: Session, today: date) -> None:
    reset_demo(db)
    s = Seeder(db, today)

    meridian = s.org("Meridian Freight Co.", "meridian-demo")
    orbital = s.org("Orbital Health Labs", "orbital-demo")

    people = [
        ("priya", "Priya Raman", "Technical Program Manager", "#a855f7", Role.owner),
        ("marcus", "Marcus Bell", "Engineering Manager", "#ec4899", Role.admin),
        ("sofia", "Sofia Okafor", "Product Owner", "#22d3ee", Role.member),
        ("daniel", "Daniel Cho", "Lead Data Engineer", "#34d399", Role.member),
        ("lena", "Lena Fischer", "Data Engineer", "#f59e0b", Role.member),
        ("aisha", "Aisha Khan", "ML Engineer", "#818cf8", Role.member),
        ("tom", "Tom Reyes", "QA Lead", "#f472b6", Role.member),
        ("ravi", "Ravi Patel", "Backend Engineer", "#60a5fa", Role.member),
        ("grace", "Grace Liu", "Frontend Engineer", "#2dd4bf", Role.member),
        ("elena", "Elena Morales", "VP, Delivery (read-only)", "#facc15", Role.viewer),
    ]
    for key, name, title, color, role in people:
        s.user(key, name, title, color)
        s.member(meridian, key, role)
    s.user("noah", "Noah Kim", "Program Director", "#fb7185")
    s.member(orbital, "noah", Role.owner)
    db.flush()

    data_team = s.team(
        meridian,
        "Data Platform",
        [
            ("daniel", "Lead Data Engineer", 30, ["CDC", "Debezium", "Spark", "Oracle"]),
            ("lena", "Data Engineer", 32, ["dbt", "SQL", "Data quality"]),
            ("tom", "QA Lead", 12, ["Reconciliation", "UAT"]),
        ],
    )
    ai_team = s.team(
        meridian,
        "Applied AI",
        [
            ("aisha", "ML Engineer", 32, ["RAG", "Evaluation", "Python"]),
            ("ravi", "Backend Engineer", 16, ["APIs", "Python"]),
            ("tom", "QA Lead", 10, ["Test design"]),
        ],
    )
    product_team = s.team(
        meridian,
        "Collaboration Squad",
        [
            ("ravi", "Backend Engineer", 20, ["APIs", "PostgreSQL"]),
            ("grace", "Frontend Engineer", 32, ["React", "Accessibility"]),
            ("tom", "QA Lead", 10, ["E2E testing"]),
        ],
    )

    _data_platform(s, meridian, data_team)
    _rag_assistant(s, meridian, ai_team)
    _team_workspaces(s, meridian, product_team)
    _orbital(s, orbital)

    # Give the lead persona a "last visit" two days ago so the briefing has something to show.
    s.users["priya"].last_seen_at = s.ts(-2, 17)
    s.users["priya"].previous_seen_at = s.ts(-2, 17)
    db.flush()


def _data_platform(s: Seeder, org, team) -> None:  # type: ignore[no-untyped-def]
    c = s.project(
        org,
        team,
        "priya",
        key="DPM",
        name="Enterprise Data Platform Migration",
        description=(
            "Migrate the on-premise Oracle order system, the SQL Server warehouse-management "
            "database and the legacy PostgreSQL billing store to a cloud lakehouse. Change data "
            "capture lands raw data in Bronze, conformed models in Silver and business marts in "
            "Gold; Power BI finance and operations reporting cuts over from the legacy SSRS estate."
        ),
        status=ProjectStatus.active,
        methodology=Methodology.hybrid,
        phase=LifecyclePhase.engineering,
        kind=ProjectKind.data_platform,
        start=-120,
        target=75,
        wip_limits={"in_progress": 4, "in_review": 3},
    )
    sprints = [
        s.sprint(c, f"DPM Sprint {i + 1}", -112 + 14 * i, -99 + 14 * i, SprintStatus.closed, 26, g)
        for i, g in enumerate(
            [
                "Profile all three source systems",
                "Stand up dev/test environments",
                "First CDC feed (billing) into Bronze",
                "Warehouse-management CDC + Bronze contracts",
                "Silver customer & shipment models",
                "Reconciliation framework v1",
                "Order CDC prerequisites",
            ]
        )
    ]
    sprints.append(
        s.sprint(c, "DPM Sprint 8", -14, -1, SprintStatus.closed, 26, "Order CDC go-live")
    )
    current = s.sprint(
        c, "DPM Sprint 9", 0, 13, SprintStatus.active, 24, "Unblock order CDC; Silver orders"
    )

    m_env = s.milestone(
        c,
        "Environments ready",
        -90,
        -85,
        "marcus",
        actual=-85,
        description="Dev/test/prod workspaces, networking, secrets and CI for pipelines.",
    )
    m_bronze = s.milestone(
        c,
        "Bronze ingestion live",
        -10,
        4,
        "daniel",
        description="All three sources replicating into Bronze with < 15 min latency.",
    )
    m_uat = s.milestone(
        c,
        "Silver/Gold UAT",
        35,
        49,
        "tom",
        description="Finance and operations sign off reconciled Gold marts.",
    )
    m_cut = s.milestone(
        c,
        "Production cut-over",
        70,
        75,
        "priya",
        description="Power BI reports switch to Gold; SSRS decommission plan approved.",
    )

    e_src = s.item(
        c, T.epic, "Source inventory & profiling", status=S.done, done_on=-95, assignee="daniel"
    )
    e_bronze = s.item(
        c,
        T.epic,
        "CDC ingestion (Bronze)",
        status=S.in_progress,
        assignee="daniel",
        milestone=m_bronze,
    )
    e_silver = s.item(
        c,
        T.epic,
        "Conformed models (Silver)",
        status=S.in_progress,
        assignee="lena",
        milestone=m_uat,
    )
    e_gold = s.item(
        c, T.epic, "Business marts (Gold)", status=S.backlog, assignee="lena", milestone=m_uat
    )
    e_dq = s.item(
        c,
        T.epic,
        "Reconciliation & data quality",
        status=S.in_progress,
        assignee="tom",
        milestone=m_uat,
    )
    e_bi = s.item(
        c, T.epic, "Power BI cut-over", status=S.backlog, assignee="sofia", milestone=m_cut
    )

    # --- completed history (drives velocity and progress) ---
    history = [
        (e_src, "Inventory tables, volumes and owners for ORDERS_DB (Oracle 19c)", 5, "daniel", 0),
        (e_src, "Profile WMS_PROD (SQL Server) — nulls, keys, update patterns", 5, "lena", 0),
        (e_src, "Profile BILLING (PostgreSQL 11) and document soft-delete semantics", 3, "lena", 0),
        (e_src, "Agree data owners and RACI for each source domain", 2, "sofia", 0),
        (e_src, "Classify PII columns across sources", 3, "tom", 0),
        (e_bronze, "Provision dev & test lakehouse workspaces with Terraform", 8, "daniel", 1),
        (e_bronze, "Pipeline CI: lint, unit tests and deploy for notebooks/jobs", 5, "lena", 1),
        (e_bronze, "Secrets management via cloud key vault for source credentials", 3, "daniel", 1),
        (e_bronze, "Debezium connector for BILLING → Bronze", 8, "daniel", 2),
        (e_bronze, "Bronze table conventions: _ingested_at, _op, _source_lsn", 3, "lena", 2),
        (e_bronze, "Schema registry and Bronze data contracts for BILLING", 5, "lena", 2),
        (e_bronze, "WMS_PROD CDC via SQL Server change tables", 8, "daniel", 3),
        (e_bronze, "Bronze data contracts for WMS shipments and stock moves", 5, "lena", 3),
        (e_bronze, "Replication-lag dashboard and alerting (< 15 min SLO)", 3, "daniel", 3),
        (e_silver, "Silver customer model with SCD2 history", 8, "lena", 4),
        (e_silver, "Silver shipment model joining WMS and billing", 8, "lena", 4),
        (e_silver, "Deduplicate late-arriving WMS events", 5, "daniel", 4),
        (e_dq, "Row-count and checksum reconciliation framework", 8, "tom", 5),
        (e_dq, "Great-Expectations-style DQ rule registry (40 rules)", 5, "lena", 5),
        (e_dq, "Daily reconciliation report to data owners", 3, "tom", 5),
        (e_bronze, "Request Oracle supplemental logging on ORDERS_DB", 2, "daniel", 6),
        (e_bronze, "Size Kafka/Event Hub throughput for order volume peaks", 3, "daniel", 6),
        (e_silver, "Silver product & pricing model", 5, "lena", 6),
        (e_dq, "Reconcile BILLING Bronze vs source (30 days)", 3, "tom", 7),
        (e_silver, "Silver invoice model (billing)", 5, "lena", 7),
    ]
    for parent, title, pts, who, sprint_idx in history:
        sp = sprints[sprint_idx]
        done = (sp.end_date - s.today).days - 1
        s.item(
            c,
            T.story,
            title,
            parent=parent,
            status=S.done,
            points=pts,
            assignee=who,
            sprint=sp,
            done_on=done,
            created=done - 20,
            milestone=m_env if sprint_idx <= 1 else None,
        )

    # --- current and upcoming work ---
    cdc_orders = s.item(
        c,
        T.story,
        "Enable CDC on ORDERS_DB order tables (Oracle LogMiner)",
        parent=e_bronze,
        status=S.blocked,
        points=8,
        assignee="daniel",
        priority=P.critical,
        sprint=current,
        milestone=m_bronze,
        start=-12,
        due=-2,
        created=-30,
        description=(
            "Blocked: the DBA team has not approved supplemental logging on the production "
            "ORDERS_DB instance pending a performance test (see DPM-R1)."
        ),
        ac=[
            "Given supplemental logging is enabled on ORDERS, ORDER_LINES and ORDER_STATUS, "
            "when a row changes in the source, then the change lands in Bronze within 15 minutes",
            "Given the connector restarts, when it resumes, then no change events are lost or "
            "duplicated (verified by LSN continuity check)",
            "Replication adds < 5% CPU on the source during the peak hour test",
        ],
        labels=["cdc", "oracle", "blocked"],
    )
    prod_net = s.item(
        c,
        T.task,
        "Private link + firewall rules from prod lakehouse to on-prem Oracle",
        parent=e_bronze,
        status=S.blocked,
        points=3,
        assignee="marcus",
        priority=P.high,
        sprint=current,
        milestone=m_bronze,
        start=-20,
        due=-6,
        created=-35,
        description="Change request CR-4471 awaiting Change Advisory Board approval.",
        labels=["network", "blocked"],
    )
    perf_test = s.item(
        c,
        T.task,
        "Run supplemental-logging performance test on ORDERS_DB replica",
        parent=e_bronze,
        status=S.in_progress,
        points=3,
        assignee="daniel",
        priority=P.high,
        sprint=current,
        start=-3,
        due=3,
        created=-8,
    )
    silver_orders = s.item(
        c,
        T.story,
        "Silver order model (orders, lines, status history)",
        parent=e_silver,
        status=S.todo,
        points=8,
        assignee="lena",
        sprint=current,
        milestone=m_uat,
        start=4,
        due=20,
        created=-25,
        ac=[
            "Given Bronze order events, when the Silver job runs, then each order has exactly one "
            "current row and a full status history",
            "Order totals reconcile to the source within 0.01%",
        ],
    )
    gold_sales = s.item(
        c,
        T.story,
        "Gold sales mart: daily revenue by lane, customer and product",
        parent=e_gold,
        status=S.backlog,
        points=8,
        assignee="lena",
        milestone=m_uat,
        start=20,
        due=34,
        created=-25,
    )
    gold_ops = s.item(
        c,
        T.story,
        "Gold operations mart: on-time delivery and dwell time",
        parent=e_gold,
        status=S.backlog,
        points=8,
        assignee="daniel",
        milestone=m_uat,
        start=14,
        due=34,
        created=-25,
    )
    recon_orders = s.item(
        c,
        T.story,
        "Reconcile order facts Bronze→Silver→Gold against Oracle",
        parent=e_dq,
        status=S.backlog,
        points=5,
        assignee="tom",
        milestone=m_uat,
        start=34,
        due=42,
        created=-20,
    )
    s.item(
        c,
        T.task,
        "DQ rules for order domain (referential + freshness)",
        parent=e_dq,
        status=S.in_progress,
        points=3,
        assignee="lena",
        sprint=current,
        start=-2,
        due=5,
        created=-10,
    )
    s.item(
        c,
        T.task,
        "Document Bronze→Silver lineage for finance auditors",
        parent=e_dq,
        status=S.in_review,
        points=2,
        assignee="tom",
        sprint=current,
        start=-6,
        due=-1,
        created=-12,
    )
    s.item(
        c,
        T.bug,
        "WMS CDC drops events during SQL Server log backup window",
        parent=e_bronze,
        status=S.in_progress,
        points=3,
        assignee="daniel",
        priority=P.high,
        sprint=current,
        start=-4,
        due=2,
        created=-5,
        description="~0.2% of stock-move events missing on 3 of the last 14 days between 01:00–01:10.",
    )
    pbi_fin = s.item(
        c,
        T.story,
        "Rebuild finance revenue report on Gold in Power BI",
        parent=e_bi,
        status=S.backlog,
        points=8,
        assignee="sofia",
        milestone=m_cut,
        start=42,
        due=60,
        created=-15,
    )
    pbi_ops = s.item(
        c,
        T.story,
        "Rebuild operations on-time report on Gold in Power BI",
        parent=e_bi,
        status=S.backlog,
        points=5,
        assignee="grace",
        milestone=m_cut,
        start=42,
        due=60,
        created=-15,
    )
    uat = s.item(
        c,
        T.task,
        "Finance & operations UAT of Gold marts and reports",
        parent=e_bi,
        status=S.backlog,
        points=5,
        assignee="tom",
        milestone=m_cut,
        start=60,
        due=68,
        created=-15,
    )
    s.item(
        c,
        T.task,
        "SSRS decommission plan and report owner sign-off",
        parent=e_bi,
        status=S.backlog,
        points=3,
        assignee="sofia",
        milestone=m_cut,
        start=55,
        due=70,
        created=-10,
    )
    s.item(
        c,
        T.task,
        "Capacity check: Power BI Premium P1 headroom for Gold refresh",
        parent=e_bi,
        status=S.todo,
        points=2,
        assignee="marcus",
        due=-4,
        created=-18,
        priority=P.medium,
    )

    for a, b in [
        (prod_net, cdc_orders),
        (perf_test, cdc_orders),
        (cdc_orders, silver_orders),
        (silver_orders, gold_sales),
        (silver_orders, gold_ops),
        (gold_sales, recon_orders),
        (gold_ops, recon_orders),
        (gold_sales, pbi_fin),
        (gold_ops, pbi_ops),
        (recon_orders, uat),
        (pbi_fin, uat),
        (pbi_ops, uat),
    ]:
        s.link(c, a, b)

    s.raid(
        c,
        RaidType.risk,
        "Supplemental logging degrades ORDERS_DB OLTP performance",
        owner="daniel",
        probability=4,
        impact=4,
        priority=P.critical,
        status=RaidStatus.in_progress,
        description="DBA team estimates 5–12% redo growth; order entry has a hard p95 SLA.",
        mitigation=f"Performance test on replica (DPM-{perf_test.number}) at 1.5× peak load; enable "
        "logging on the three order tables only, not database-wide.",
        contingency="Fall back to hourly incremental extracts on ORDER_STATUS until a window opens.",
        trigger="Test shows > 5% CPU or > 10% redo increase, or DBA approval not given by "
        f"{s.d(5)}.",
        evidence="DBA review notes 2 weeks ago; CR-4471 comments.",
        milestone=m_bronze,
        items=[cdc_orders, perf_test],
        created=-21,
        due=5,
    )
    s.raid(
        c,
        RaidType.risk,
        "Undocumented schema changes in legacy ERP break Bronze contracts",
        owner="lena",
        probability=3,
        impact=4,
        priority=P.high,
        mitigation="Schema registry in compatibility mode; nightly contract diff alert to owners.",
        trigger="Two contract breaks in any 30-day window.",
        created=-60,
    )
    s.raid(
        c,
        RaidType.issue,
        "Firewall change CR-4471 stuck in Change Advisory Board",
        owner="marcus",
        impact=4,
        priority=P.high,
        status=RaidStatus.open,
        description="CAB deferred twice; prod connectivity to ORDERS_DB is unavailable.",
        mitigation="Escalate to infrastructure director with Bronze milestone impact.",
        items=[prod_net],
        milestone=m_bronze,
        created=-12,
        due=2,
    )
    s.raid(
        c,
        RaidType.risk,
        "Finance reconciliation tolerance not agreed before UAT",
        owner="sofia",
        probability=3,
        impact=3,
        priority=P.medium,
        mitigation="Decision DPM-D3 proposed; review at steering committee.",
        created=-9,
        milestone=m_uat,
    )
    s.raid(
        c,
        RaidType.assumption,
        "Power BI Premium P1 capacity can absorb Gold refreshes",
        owner="marcus",
        impact=3,
        priority=P.medium,
        status=RaidStatus.monitoring,
        description="Assumed 35% headroom based on last quarter's metrics; not yet validated.",
        created=-40,
    )
    s.raid(
        c,
        RaidType.dependency,
        "Network team delivers prod private link",
        owner="marcus",
        impact=5,
        priority=P.high,
        status=RaidStatus.open,
        description="External dependency on Infrastructure; required for order CDC in prod.",
        items=[prod_net],
        due=-6,
        created=-35,
    )
    s.raid(
        c,
        RaidType.risk,
        "Key-person dependency on lead data engineer for CDC",
        owner="priya",
        probability=3,
        impact=3,
        priority=P.medium,
        status=RaidStatus.monitoring,
        mitigation="Pair Lena on Debezium runbooks; record connector recovery procedures.",
        created=-50,
    )

    s.decision(
        c,
        "Use log-based CDC (Debezium) instead of nightly batch extracts",
        decision="Replicate all three sources with log-based CDC into Bronze.",
        context="Finance needs intraday revenue; nightly extracts miss deletes and corrections.",
        rationale="Captures deletes and updates, lowers source load vs full extracts, near-real-time.",
        alternatives=[
            {
                "option": "Nightly full extracts",
                "pros": "Simple",
                "cons": "Misses deletes; heavy load",
            },
            {
                "option": "Vendor replication tool",
                "pros": "Managed",
                "cons": "Licence cost; lock-in",
            },
        ],
        impact="Requires supplemental logging on Oracle (see DPM-R1).",
        by="marcus",
        on=-100,
    )
    s.decision(
        c,
        "Adopt medallion architecture (Bronze/Silver/Gold) on Delta tables",
        decision="Raw CDC in Bronze, conformed entities in Silver, consumption marts in Gold.",
        rationale="Separates replay-able raw history from business logic; clear contracts per layer.",
        by="daniel",
        on=-98,
    )
    s.decision(
        c,
        "Reconciliation tolerance of 0.01% for financial facts",
        decision="Gold revenue facts must reconcile to source within 0.01% per day per lane.",
        context="Finance asked for exact match; exact match is infeasible with FX rounding.",
        status=DecisionStatus.proposed,
        by="sofia",
        on=-3,
    )

    # Recent activity from teammates (shows up in "since your last visit").
    s.event(
        c,
        "work_item",
        cdc_orders.id,
        "daniel",
        "update",
        f"Moved DPM-{cdc_orders.number} from in_progress to blocked",
        -1.5,
        {"status": {"from": "in_progress", "to": "blocked"}},
    )
    s.event(
        c,
        "milestone",
        m_bronze.id,
        "daniel",
        "update",
        "Moved milestone 'Bronze ingestion live' forecast to " + str(s.d(4)),
        -1.2,
    )
    s.event(
        c,
        "work_item",
        perf_test.id,
        "daniel",
        "update",
        f"Moved DPM-{perf_test.number} from todo to in_progress",
        -0.8,
        {"status": {"from": "todo", "to": "in_progress"}},
    )


def _rag_assistant(s: Seeder, org, team) -> None:  # type: ignore[no-untyped-def]
    c = s.project(
        org,
        team,
        "sofia",
        key="RAG",
        name="AI Customer Support Assistant",
        description=(
            "Retrieval-augmented assistant that answers shipment, billing and claims questions "
            "for Meridian customers from the help centre, policy documents and order status API, "
            "with human hand-off. Release is gated on accuracy, safety and privacy evaluations."
        ),
        status=ProjectStatus.active,
        methodology=Methodology.scrum,
        phase=LifecyclePhase.testing,
        kind=ProjectKind.ai_product,
        start=-84,
        target=30,
        wip_limits={"in_progress": 4},
    )
    sprints = [
        s.sprint(c, f"RAG Sprint {i + 1}", -84 + 14 * i, -71 + 14 * i, SprintStatus.closed, 20, g)
        for i, g in enumerate(
            [
                "Discovery: top intents and success metrics",
                "Ingest help centre; baseline retrieval",
                "Hybrid retrieval + citations",
                "Golden eval set and harness",
                "Safety, PII and tone",
                "Hand-off and order-status tool",
            ]
        )
    ]
    current = s.sprint(
        c, "RAG Sprint 7", 0, 13, SprintStatus.active, 20, "Close accuracy gap on billing intents"
    )

    m_eval = s.milestone(
        c,
        "Eval baseline agreed",
        -56,
        -56,
        "sofia",
        actual=-57,
        description="Metrics, thresholds and golden dataset signed off.",
    )
    m_safety = s.milestone(
        c,
        "Safety & privacy review passed",
        7,
        10,
        "aisha",
        description="Red-team, PII and bias review signed by AI governance board.",
    )
    m_pilot = s.milestone(c, "Pilot launch (10% of chat traffic)", 28, 28, "sofia")

    e_disc = s.item(c, T.epic, "Use-case discovery", status=S.done, done_on=-60, assignee="sofia")
    e_ingest = s.item(
        c, T.epic, "Knowledge ingestion & indexing", status=S.done, done_on=-30, assignee="aisha"
    )
    e_prompt = s.item(
        c, T.epic, "Prompt & retrieval design", status=S.in_progress, assignee="aisha"
    )
    e_eval = s.item(
        c, T.epic, "Evaluation & safety", status=S.in_progress, assignee="tom", milestone=m_safety
    )
    e_pilot = s.item(
        c, T.epic, "Pilot & rollout", status=S.backlog, assignee="sofia", milestone=m_pilot
    )

    history = [
        (e_disc, "Analyse 6 months of chat transcripts for top 20 intents", 5, "sofia", 0),
        (e_disc, "Define success metrics: containment, CSAT, accuracy", 3, "sofia", 0),
        (e_ingest, "Ingest and chunk 1,850 help-centre articles", 5, "aisha", 1),
        (e_ingest, "Index policy PDFs with section-aware chunking", 5, "aisha", 1),
        (e_prompt, "Baseline dense retrieval and answer prompt", 5, "aisha", 1),
        (e_prompt, "Hybrid retrieval (BM25 + vectors) with reciprocal rank fusion", 8, "aisha", 2),
        (e_prompt, "Answer citations linking to source articles", 3, "ravi", 2),
        (e_eval, "Golden eval set: 320 questions with reference answers", 8, "tom", 3),
        (e_eval, "Automated eval harness (accuracy, groundedness, refusal)", 5, "aisha", 3),
        (e_eval, "PII redaction for transcripts before indexing", 5, "ravi", 4),
        (e_eval, "Tone and policy-compliance rubric", 3, "tom", 4),
        (e_pilot, "Human hand-off when confidence < threshold", 5, "ravi", 5),
        (e_prompt, "Order-status tool call with customer verification", 8, "ravi", 5),
    ]
    for parent, title, pts, who, idx in history:
        sp = sprints[idx]
        done = (sp.end_date - s.today).days - 1
        s.item(
            c,
            T.story,
            title,
            parent=parent,
            status=S.done,
            points=pts,
            assignee=who,
            sprint=sp,
            done_on=done,
            created=done - 18,
            milestone=m_eval if idx == 3 else None,
        )

    billing = s.item(
        c,
        T.story,
        "Raise billing-intent accuracy from 78% to ≥ 85%",
        parent=e_prompt,
        status=S.in_progress,
        points=8,
        assignee="aisha",
        priority=P.critical,
        sprint=current,
        milestone=m_safety,
        start=-2,
        due=9,
        created=-12,
        description="Last eval run: billing intents 78.4% (n=74), overall 86.9% (n=320).",
        ac=[
            "Given the golden set, when the eval harness runs, then billing-intent accuracy is ≥ 85% "
            "with no regression > 1 pt on other intents",
            "Every answer cites at least one retrieved source",
        ],
        labels=["accuracy", "eval"],
    )
    redteam = s.item(
        c,
        T.story,
        "Red-team: prompt injection and data-exfiltration tests",
        parent=e_eval,
        status=S.in_progress,
        points=5,
        assignee="tom",
        priority=P.high,
        sprint=current,
        milestone=m_safety,
        start=-3,
        due=6,
        created=-14,
        ac=[
            "Given 60 adversarial prompts, when run against the assistant, then 0 disclose another "
            "customer's data and ≥ 95% are refused or safely deflected",
        ],
    )
    bias = s.item(
        c,
        T.story,
        "Bias & tone review across customer segments",
        parent=e_eval,
        status=S.todo,
        points=3,
        assignee="tom",
        sprint=current,
        milestone=m_safety,
        start=2,
        due=8,
        created=-14,
    )
    dpia = s.item(
        c,
        T.task,
        "Data privacy impact assessment sign-off",
        parent=e_eval,
        status=S.in_review,
        points=2,
        assignee="sofia",
        priority=P.high,
        milestone=m_safety,
        due=-1,
        created=-20,
    )
    latency = s.item(
        c,
        T.story,
        "Meet latency budget: p95 < 2.5 s end-to-end",
        parent=e_prompt,
        status=S.todo,
        points=5,
        assignee="ravi",
        sprint=current,
        start=1,
        due=10,
        created=-10,
        description="Current p95 3.4 s in load test; retrieval 0.6 s, generation 2.5 s.",
    )
    s.item(
        c,
        T.bug,
        "Citations point to archived article versions",
        parent=e_prompt,
        status=S.in_progress,
        points=2,
        assignee="ravi",
        sprint=current,
        priority=P.medium,
        start=-1,
        due=3,
        created=-4,
    )
    pilot_cfg = s.item(
        c,
        T.story,
        "Pilot feature flag and 10% traffic routing",
        parent=e_pilot,
        status=S.backlog,
        points=3,
        assignee="ravi",
        milestone=m_pilot,
        start=14,
        due=24,
        created=-8,
    )
    s.item(
        c,
        T.story,
        "Pilot monitoring dashboard: containment, CSAT, escalations",
        parent=e_pilot,
        status=S.backlog,
        points=5,
        assignee="grace",
        milestone=m_pilot,
        start=14,
        due=26,
        created=-8,
    )
    s.item(
        c,
        T.task,
        "Agent playbook for hand-off conversations",
        parent=e_pilot,
        status=S.backlog,
        points=2,
        assignee="sofia",
        milestone=m_pilot,
        due=24,
        created=-8,
    )

    for a, b in [
        (billing, pilot_cfg),
        (redteam, pilot_cfg),
        (bias, pilot_cfg),
        (dpia, pilot_cfg),
        (latency, pilot_cfg),
    ]:
        s.link(c, a, b)

    s.raid(
        c,
        RaidType.risk,
        "Billing-intent accuracy stays below 85% release threshold",
        owner="aisha",
        probability=3,
        impact=5,
        priority=P.critical,
        status=RaidStatus.in_progress,
        description="78.4% on last eval run; billing policies changed in Q3 and KB lags.",
        mitigation="Refresh billing KB articles; add structured invoice lookup tool; re-run eval.",
        contingency="Exclude billing intents from pilot scope and route to human agents.",
        trigger="Accuracy < 85% on the eval run before the safety review.",
        milestone=m_safety,
        items=[billing],
        created=-10,
        due=8,
    )
    s.raid(
        c,
        RaidType.risk,
        "Help-centre articles out of date for new surcharge policy",
        owner="sofia",
        probability=4,
        impact=3,
        priority=P.high,
        mitigation="Content owners review 140 flagged articles; freshness date in index.",
        created=-18,
    )
    s.raid(
        c,
        RaidType.issue,
        "Model provider rate limits hit during load test",
        owner="ravi",
        impact=3,
        priority=P.medium,
        status=RaidStatus.in_progress,
        mitigation="Request quota increase; add response caching for top FAQs.",
        created=-6,
    )
    s.raid(
        c,
        RaidType.assumption,
        "Customer verification API available for pilot",
        owner="ravi",
        impact=4,
        priority=P.medium,
        status=RaidStatus.monitoring,
        created=-30,
    )

    s.decision(
        c,
        "Hybrid retrieval (BM25 + vectors) with reciprocal rank fusion",
        decision="Use hybrid retrieval for all intents.",
        rationale="+9 pts answer accuracy vs dense-only on the golden set; better on SKU/IDs.",
        alternatives=[{"option": "Dense only", "pros": "Simpler", "cons": "Misses exact IDs"}],
        by="aisha",
        on=-50,
    )
    s.decision(
        c,
        "Hand off to a human when confidence < 0.6 or customer asks",
        decision="Confidence threshold 0.6; explicit 'talk to a person' always honoured.",
        by="sofia",
        on=-25,
    )
    s.decision(
        c,
        "Production model tier for pilot",
        decision="Pending eval results: compare mid-tier vs top-tier model on cost per resolved chat.",
        status=DecisionStatus.proposed,
        by="sofia",
        on=-2,
    )
    s.event(
        c,
        "work_item",
        billing.id,
        "aisha",
        "update",
        f"Updated RAG-{billing.number}: description (new eval run 78.4%)",
        -1.0,
    )


def _team_workspaces(s: Seeder, org, team) -> None:  # type: ignore[no-untyped-def]
    c = s.project(
        org,
        team,
        "marcus",
        key="TWS",
        name="Team Workspaces",
        description=(
            "Shared workspaces for customer logistics teams in the Meridian shipper portal: "
            "invitations, roles, shared saved views and activity history."
        ),
        status=ProjectStatus.active,
        methodology=Methodology.scrum,
        phase=LifecyclePhase.engineering,
        kind=ProjectKind.software,
        start=-80,
        target=40,
        wip_limits={"in_progress": 3, "in_review": 2},
    )
    windows = [(-76, -63), (-62, -49), (-48, -35), (-34, -21), (-20, -7)]
    goals = [
        "Workspace data model and API",
        "Invitations and roles",
        "Shared saved views",
        "Activity history",
        "Beta hardening",
    ]
    sprints = [
        s.sprint(c, f"TWS Sprint {i + 1}", a, b, SprintStatus.closed, 24, goals[i])
        for i, (a, b) in enumerate(windows)
    ]
    current = s.sprint(c, "TWS Sprint 6", -6, 7, SprintStatus.active, 24, "Beta release readiness")
    s.sprint(c, "TWS Sprint 7", 8, 21, SprintStatus.planned, 24, "GA polish and docs")

    m_design = s.milestone(c, "Design sign-off", -66, -66, "sofia", actual=-67)
    m_beta = s.milestone(c, "Beta release", 10, 12, "marcus")
    m_ga = s.milestone(c, "General availability", 40, 40, "marcus")

    e_core = s.item(c, T.epic, "Workspaces core", status=S.done, done_on=-36, assignee="ravi")
    e_collab = s.item(
        c, T.epic, "Collaboration", status=S.in_progress, assignee="grace", milestone=m_beta
    )
    e_launch = s.item(c, T.epic, "Launch", status=S.backlog, assignee="sofia", milestone=m_ga)

    done_by_sprint = [
        [
            ("Workspace schema & migrations", 5, "ravi"),
            ("Workspace CRUD API", 5, "ravi"),
            ("Workspace switcher UI", 5, "grace"),
            ("Design review: workspace IA", 3, "sofia"),
        ],
        [
            ("Email invitations with expiring tokens", 8, "ravi"),
            ("Role model: owner/editor/viewer", 5, "ravi"),
            ("Members management page", 8, "grace"),
            ("Audit invitation acceptance", 2, "tom"),
        ],
        [
            ("Saved views API", 5, "ravi"),
            ("Share view with workspace", 5, "grace"),
            ("Views list with filters", 5, "grace"),
            ("Permission checks on shared views", 3, "ravi"),
        ],
        [
            ("Activity history API", 8, "ravi"),
            ("Activity feed UI", 8, "grace"),
            ("E2E tests: invitations and roles", 5, "tom"),
            ("Fix N+1 on members page", 2, "ravi"),
        ],
        [
            ("Rate limiting on invitation endpoint", 3, "ravi"),
            ("Accessibility pass on workspace pages", 5, "grace"),
            ("Beta feedback survey", 2, "sofia"),
            ("Load test 5k-member workspace", 5, "tom"),
            ("Empty states and onboarding hints", 3, "grace"),
        ],
    ]
    parents = [e_core, e_core, e_collab, e_collab, e_collab]
    for idx, stories in enumerate(done_by_sprint):
        sp = sprints[idx]
        for j, (title, pts, who) in enumerate(stories):
            done = (sp.end_date - s.today).days - (len(stories) - j)
            s.item(
                c,
                T.story,
                title,
                parent=parents[idx],
                status=S.done,
                points=pts,
                assignee=who,
                sprint=sp,
                done_on=done,
                created=done - 16,
                milestone=m_design if idx == 0 and j == 3 else None,
            )
    # One spillover from sprint 5 into sprint 6.
    s.item(
        c,
        T.story,
        "Workspace-level notification preferences",
        parent=e_collab,
        status=S.in_review,
        points=5,
        assignee="grace",
        sprint=current,
        milestone=m_beta,
        start=-10,
        due=-2,
        created=-24,
        priority=P.high,
        ac=[
            "Given a member, when they mute a workspace, then they receive no email digests for it"
        ],
    )
    s.item(
        c,
        T.story,
        "Transfer workspace ownership",
        parent=e_collab,
        status=S.in_progress,
        points=5,
        assignee="ravi",
        sprint=current,
        milestone=m_beta,
        start=-4,
        due=4,
        created=-14,
        ac=[
            "Given an owner, when they transfer ownership to an editor, then roles swap atomically "
            "and both receive a confirmation email"
        ],
    )
    s.item(
        c,
        T.story,
        "Remove member and revoke access to shared views",
        parent=e_collab,
        status=S.todo,
        points=3,
        assignee="ravi",
        sprint=current,
        milestone=m_beta,
        due=6,
        created=-14,
    )
    s.item(
        c,
        T.bug,
        "Invitation link 500s when invitee already a member",
        parent=e_collab,
        status=S.in_progress,
        points=2,
        assignee="ravi",
        sprint=current,
        priority=P.high,
        start=-2,
        due=1,
        created=-3,
    )
    s.item(
        c,
        T.bug,
        "Activity feed timestamps ignore user timezone",
        parent=e_collab,
        status=S.todo,
        points=1,
        assignee="grace",
        sprint=current,
        priority=P.low,
        due=7,
        created=-5,
    )
    s.item(
        c,
        T.task,
        "Beta release notes and help article",
        parent=e_launch,
        status=S.todo,
        points=2,
        assignee="sofia",
        sprint=current,
        milestone=m_beta,
        due=8,
        created=-7,
    )
    s.item(
        c,
        T.story,
        "Usage analytics events for workspaces",
        parent=e_launch,
        status=S.backlog,
        points=3,
        assignee="ravi",
        milestone=m_ga,
        created=-7,
    )
    s.item(
        c,
        T.story,
        "Admin export of workspace members (CSV)",
        parent=e_launch,
        status=S.backlog,
        points=3,
        milestone=m_ga,
        created=-7,
    )
    s.item(
        c,
        T.story,
        "Pricing-tier limits on workspace count",
        parent=e_launch,
        status=S.backlog,
        milestone=m_ga,
        created=-5,
        description="Needs pricing decision before estimation.",
    )

    s.raid(
        c,
        RaidType.risk,
        "Email deliverability for invitations in enterprise domains",
        owner="ravi",
        probability=2,
        impact=3,
        priority=P.medium,
        status=RaidStatus.monitoring,
        mitigation="SPF/DKIM verified; fallback copy-link invite.",
        created=-40,
    )
    s.raid(
        c,
        RaidType.risk,
        "Pricing limits undecided may delay GA scope",
        owner="sofia",
        probability=3,
        impact=3,
        priority=P.medium,
        mitigation="Decision TWS-D2 scheduled for next product council.",
        created=-6,
        milestone=m_ga,
    )
    s.decision(
        c,
        "Three roles only (owner, editor, viewer) for v1",
        decision="Ship three fixed roles; custom roles deferred.",
        rationale="Covers 92% of interviewed teams; custom roles triple test surface.",
        by="sofia",
        on=-60,
    )
    s.decision(
        c,
        "Workspace limits per pricing tier",
        decision="Free: 1 workspace, Team: 5, Enterprise: unlimited (proposed).",
        status=DecisionStatus.proposed,
        by="sofia",
        on=-5,
    )


def _orbital(s: Seeder, org) -> None:  # type: ignore[no-untyped-def]
    c = s.project(
        org,
        None,
        "noah",
        key="CTP",
        name="Clinical Trials Portal",
        description="Confidential to Orbital Health Labs — used to demonstrate tenant isolation.",
        status=ProjectStatus.active,
        methodology=Methodology.kanban,
        phase=LifecyclePhase.requirements,
        kind=ProjectKind.software,
        start=-20,
        target=120,
    )
    s.item(c, T.epic, "Participant onboarding", status=S.in_progress, assignee="noah")
    s.raid(
        c,
        RaidType.risk,
        "Regulatory review timeline uncertain",
        owner="noah",
        probability=3,
        impact=4,
        created=-10,
    )
