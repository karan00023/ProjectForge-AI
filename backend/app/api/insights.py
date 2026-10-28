"""Read models that aggregate across projects: command center, activity feed, global search."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import Float, func, literal, or_, select
from sqlalchemy.orm import Session

from app.api.projects import summarize
from app.api.scoped import decision_out, get_project, project_keys, raid_out, work_item_out
from app.core.deps import DB, Ctx, CtxDep, Today
from app.models import AuditEvent, Decision, Milestone, Project, RaidItem, WorkItem
from app.models.enums import (
    CLOSED_STATUSES,
    OPEN_RAID_STATUSES,
    DecisionStatus,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    RaidType,
    WorkItemStatus,
)
from app.schemas import AuditOut, DashboardOut, DeadlineOut, Kpi, SearchHit
from app.services.health import DELIVERY_TYPES, RISK_RED_SCORE

router = APIRouter(tags=["insights"])

DEADLINE_HORIZON_DAYS = 21


def _live_projects(db: Session, ctx: Ctx) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.organization_id == ctx.org_id, Project.deleted_at.is_(None))
            .order_by(Project.name)
        )
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(ctx: CtxDep, db: DB, today: Today) -> DashboardOut:
    projects = _live_projects(db, ctx)
    ids = [p.id for p in projects]
    keys = {p.id: p.key for p in projects}
    summaries = summarize(db, ctx, projects, today)
    now = datetime.now(UTC)

    completed_14d = (
        db.scalar(
            select(func.count()).where(
                WorkItem.organization_id == ctx.org_id,
                WorkItem.project_id.in_(ids),
                WorkItem.deleted_at.is_(None),
                WorkItem.type.in_(DELIVERY_TYPES),
                WorkItem.status == WorkItemStatus.done,
                WorkItem.completed_at >= now - timedelta(days=14),
            )
        )
        or 0
    )

    completed_ms = db.execute(
        select(Milestone.baseline_date, Milestone.actual_date).where(
            Milestone.organization_id == ctx.org_id,
            Milestone.project_id.in_(ids),
            Milestone.deleted_at.is_(None),
            Milestone.status == MilestoneStatus.completed,
            Milestone.actual_date.is_not(None),
        )
    ).all()
    on_time = sum(1 for b, a in completed_ms if a is not None and a <= b)

    open_raid = list(
        db.scalars(
            select(RaidItem).where(
                RaidItem.organization_id == ctx.org_id,
                RaidItem.project_id.in_(ids),
                RaidItem.deleted_at.is_(None),
                RaidItem.status.in_(OPEN_RAID_STATUSES),
            )
        )
    )
    critical = sorted(
        (
            r
            for r in open_raid
            if (r.type == RaidType.risk and (r.score or 0) >= RISK_RED_SCORE)
            or (r.type == RaidType.issue and r.priority == Priority.critical)
        ),
        key=lambda r: -(r.score or 25),
    )

    blocked = db.scalars(
        select(WorkItem)
        .where(
            WorkItem.organization_id == ctx.org_id,
            WorkItem.project_id.in_(ids),
            WorkItem.deleted_at.is_(None),
            WorkItem.status == WorkItemStatus.blocked,
        )
        .order_by(WorkItem.priority, WorkItem.updated_at)
    ).all()

    horizon = today + timedelta(days=DEADLINE_HORIZON_DAYS)
    deadlines: list[DeadlineOut] = []
    for m in db.scalars(
        select(Milestone).where(
            Milestone.organization_id == ctx.org_id,
            Milestone.project_id.in_(ids),
            Milestone.deleted_at.is_(None),
            Milestone.status == MilestoneStatus.open,
            Milestone.planned_date <= horizon,
        )
    ):
        deadlines.append(
            DeadlineOut(
                entity_type="milestone",
                id=m.id,
                project_id=m.project_id,
                project_key=keys[m.project_id],
                label="Milestone",
                title=m.name,
                date=m.planned_date,
                overdue=m.planned_date < today,
            )
        )
    for w in db.scalars(
        select(WorkItem).where(
            WorkItem.organization_id == ctx.org_id,
            WorkItem.project_id.in_(ids),
            WorkItem.deleted_at.is_(None),
            WorkItem.status.not_in(CLOSED_STATUSES),
            WorkItem.due_date.is_not(None),
            WorkItem.due_date <= horizon,
        )
    ):
        assert w.due_date is not None
        deadlines.append(
            DeadlineOut(
                entity_type="work_item",
                id=w.id,
                project_id=w.project_id,
                project_key=keys[w.project_id],
                label=f"{keys[w.project_id]}-{w.number}",
                title=w.title,
                date=w.due_date,
                overdue=w.due_date < today,
            )
        )
    deadlines.sort(key=lambda d: (d.date, d.entity_type != "milestone"))

    pending = db.scalars(
        select(Decision)
        .where(
            Decision.organization_id == ctx.org_id,
            Decision.project_id.in_(ids),
            Decision.deleted_at.is_(None),
            Decision.status == DecisionStatus.proposed,
        )
        .order_by(Decision.created_at)
    ).all()

    activity = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.organization_id == ctx.org_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(15)
    ).all()

    since = ctx.user.previous_seen_at
    changes_since = 0
    if since is not None:
        changes_since = (
            db.scalar(
                select(func.count()).where(
                    AuditEvent.organization_id == ctx.org_id,
                    AuditEvent.created_at > since,
                    or_(
                        AuditEvent.actor_user_id.is_(None), AuditEvent.actor_user_id != ctx.user.id
                    ),
                )
            )
            or 0
        )

    active = sum(1 for p in projects if p.status == ProjectStatus.active)
    at_risk = sum(1 for s in summaries if s.health.level == "red")
    kpis = [
        Kpi(
            id="active_projects",
            label="Active projects",
            value=active,
            display=str(active),
            definition="Projects with status 'active' in this organization.",
            numerator=active,
            denominator=len(projects),
        ),
        Kpi(
            id="projects_red",
            label="Projects in red",
            value=at_risk,
            display=str(at_risk),
            definition="Projects where at least one red health rule fired today.",
            numerator=at_risk,
            denominator=len(projects),
        ),
        Kpi(
            id="completed_14d",
            label="Completed (14 days)",
            value=completed_14d,
            display=str(completed_14d),
            definition="Stories, tasks and bugs moved to done in the last 14 days.",
        ),
        Kpi(
            id="milestone_on_time",
            label="Milestones on time",
            value=(on_time / len(completed_ms)) if completed_ms else None,
            display=f"{round(100 * on_time / len(completed_ms))}%" if completed_ms else "—",
            definition="Completed milestones whose actual date is on or before their baseline "
            "date. Shows '—' until a milestone has been completed.",
            numerator=on_time,
            denominator=len(completed_ms),
        ),
        Kpi(
            id="critical_raid",
            label="Critical risks & issues",
            value=len(critical),
            display=str(len(critical)),
            definition=f"Open risks scoring ≥ {RISK_RED_SCORE} plus open critical issues.",
        ),
    ]

    return DashboardOut(
        evaluated_on=today,
        kpis=kpis,
        projects=summaries,
        critical_risks=[raid_out(r, keys[r.project_id]) for r in critical[:10]],
        blocked_items=[work_item_out(w, keys[w.project_id]) for w in blocked[:10]],
        deadlines=deadlines[:15],
        pending_decisions=[decision_out(d, keys[d.project_id]) for d in pending[:10]],
        recent_activity=[AuditOut.model_validate(a) for a in activity],
        changes_since_last_visit=changes_since,
    )


@router.get("/activity", response_model=list[AuditOut])
def activity(
    ctx: CtxDep,
    db: DB,
    project_id: uuid.UUID | None = None,
    since: datetime | None = None,
    before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(AuditEvent.organization_id == ctx.org_id)
    if project_id:
        query = query.where(AuditEvent.project_id == get_project(db, ctx, project_id).id)
    if since:
        query = query.where(AuditEvent.created_at > since)
    if before:
        query = query.where(AuditEvent.created_at < before)
    return list(db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(limit)))


_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]{1,7})-(R|D)?(\d+)$")


@router.get("/search", response_model=list[SearchHit])
def search(
    ctx: CtxDep,
    db: DB,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[SearchHit]:
    keys = project_keys(db, ctx)
    live_projects = select(Project.id).where(
        Project.organization_id == ctx.org_id, Project.deleted_at.is_(None)
    )
    hits: list[SearchHit] = []

    # Exact key lookup, e.g. "DPM-12", "DPM-R3", "DPM-D2".
    match = _KEY_RE.match(q.strip())
    if match:
        key, kind, number = match.group(1).upper(), match.group(2), int(match.group(3))
        project_id = next((pid for pid, k in keys.items() if k == key), None)
        if project_id is not None:
            model: Any = {None: WorkItem, "R": RaidItem, "D": Decision}[kind]
            entity_type = {None: "work_item", "R": "raid_item", "D": "decision"}[kind]
            obj = db.scalar(
                select(model).where(
                    model.project_id == project_id,
                    model.number == number,
                    model.deleted_at.is_(None),
                )
            )
            if obj is not None:
                hits.append(
                    SearchHit(
                        entity_type=entity_type,
                        id=obj.id,
                        project_id=project_id,
                        label=f"{key}-{kind or ''}{number}",
                        title=obj.title,
                        snippet=None,
                        rank=100.0,
                    )
                )

    tsq = func.websearch_to_tsquery("english", q)
    sources: list[tuple[str, Any, Any, Any, Any, Any]] = [
        ("project", Project, Project.name, Project.description, Project.id, None),
        (
            "work_item",
            WorkItem,
            WorkItem.title,
            WorkItem.description,
            WorkItem.project_id,
            WorkItem.number,
        ),
        (
            "raid_item",
            RaidItem,
            RaidItem.title,
            RaidItem.description,
            RaidItem.project_id,
            RaidItem.number,
        ),
        (
            "decision",
            Decision,
            Decision.title,
            Decision.decision,
            Decision.project_id,
            Decision.number,
        ),
    ]
    prefix = {"work_item": "", "raid_item": "R", "decision": "D"}
    seen = {h.id for h in hits}
    for entity_type, model, title_col, body_col, project_col, number_col in sources:
        rank = func.ts_rank(model.search_vector, tsq).cast(Float)
        snippet = func.ts_headline(
            "english",
            func.coalesce(body_col, ""),
            tsq,
            "MaxWords=18, MinWords=6, StartSel=«, StopSel=»",
        )
        rows = db.execute(
            select(
                model.id,
                project_col.label("project_id"),
                title_col.label("title"),
                (number_col if number_col is not None else literal(None)).label("number"),
                snippet.label("snippet"),
                rank.label("rank"),
            )
            .where(
                model.organization_id == ctx.org_id,
                model.deleted_at.is_(None),
                project_col.in_(live_projects),
                model.search_vector.op("@@")(tsq),
            )
            .order_by(rank.desc())
            .limit(limit)
        ).all()
        for r in rows:
            if r.id in seen:
                continue
            key = keys.get(r.project_id, "")
            label = key if entity_type == "project" else f"{key}-{prefix[entity_type]}{r.number}"
            hits.append(
                SearchHit(
                    entity_type=entity_type,
                    id=r.id,
                    project_id=r.project_id,
                    label=label,
                    title=r.title,
                    snippet=r.snippet or None,
                    rank=float(r.rank),
                )
            )
    hits.sort(key=lambda h: -h.rank)
    return hits[:limit]
