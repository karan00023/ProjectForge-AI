import uuid
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.scoped import ensure_member, get_project, get_scoped
from app.core import audit
from app.core.deps import DB, Ctx, CtxDep, Today, Writer
from app.core.errors import bad_request
from app.models import Milestone, Sprint, WorkItem
from app.models.base import utcnow
from app.models.enums import MilestoneStatus, WorkItemStatus
from app.schemas import (
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
    RebaselineIn,
    SprintCreate,
    SprintOut,
    SprintUpdate,
)
from app.services.calendar import working_days_between

router = APIRouter(tags=["planning"])


def milestones_out(
    db: Session, ctx: Ctx, milestones: list[Milestone], today: date
) -> list[MilestoneOut]:
    ids = [m.id for m in milestones]
    counts: dict[uuid.UUID | None, list[int]] = defaultdict(lambda: [0, 0])
    if ids:
        rows = db.execute(
            select(WorkItem.milestone_id, WorkItem.status).where(
                WorkItem.organization_id == ctx.org_id,
                WorkItem.milestone_id.in_(ids),
                WorkItem.deleted_at.is_(None),
                WorkItem.status != WorkItemStatus.cancelled,
            )
        ).all()
        for milestone_id, item_status in rows:
            counts[milestone_id][0] += 1
            counts[milestone_id][1] += int(item_status == WorkItemStatus.done)
    return [
        MilestoneOut(
            id=m.id,
            project_id=m.project_id,
            name=m.name,
            description=m.description,
            baseline_date=m.baseline_date,
            planned_date=m.planned_date,
            actual_date=m.actual_date,
            status=m.status,
            owner_id=m.owner_id,
            variance_working_days=working_days_between(
                m.baseline_date, m.actual_date or m.planned_date
            ),
            overdue=m.status == MilestoneStatus.open and m.planned_date < today,
            deliverables_total=counts[m.id][0],
            deliverables_done=counts[m.id][1],
        )
        for m in milestones
    ]


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneOut])
def list_milestones(project_id: uuid.UUID, ctx: CtxDep, db: DB, today: Today) -> list[MilestoneOut]:
    project = get_project(db, ctx, project_id)
    ms = db.scalars(
        select(Milestone)
        .where(Milestone.project_id == project.id, Milestone.deleted_at.is_(None))
        .order_by(Milestone.planned_date)
    ).all()
    return milestones_out(db, ctx, list(ms), today)


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneOut,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: uuid.UUID, body: MilestoneCreate, ctx: Writer, db: DB, today: Today
) -> MilestoneOut:
    project = get_project(db, ctx, project_id)
    ensure_member(db, ctx, body.owner_id, "owner_id")
    m = Milestone(
        id=uuid.uuid4(),
        organization_id=ctx.org_id,
        project_id=project.id,
        name=body.name,
        description=body.description,
        baseline_date=body.planned_date,
        planned_date=body.planned_date,
        owner_id=body.owner_id,
    )
    db.add(m)
    db.flush()
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="milestone",
        entity_id=m.id,
        project_id=project.id,
        summary=f"Created milestone '{m.name}' for {m.planned_date.isoformat()}",
    )
    return milestones_out(db, ctx, [m], today)[0]


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: uuid.UUID, body: MilestoneUpdate, ctx: Writer, db: DB, today: Today
) -> MilestoneOut:
    m = get_scoped(db, ctx, Milestone, milestone_id)
    updates = body.model_dump(exclude_unset=True)
    for required in ("name", "planned_date", "status"):
        if required in updates and updates[required] is None:
            raise bad_request(f"{required} cannot be null")
    if "owner_id" in updates:
        ensure_member(db, ctx, updates["owner_id"], "owner_id")
    if updates.get("status") == MilestoneStatus.completed and not updates.get("actual_date"):
        updates["actual_date"] = m.actual_date or today
    changes = audit.diff(m, updates)
    if changes:
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="milestone",
            entity_id=m.id,
            project_id=m.project_id,
            summary=f"Updated milestone '{m.name}': {', '.join(changes)}",
            changes=changes,
        )
    return milestones_out(db, ctx, [m], today)[0]


@router.post("/milestones/{milestone_id}/rebaseline", response_model=MilestoneOut)
def rebaseline_milestone(
    milestone_id: uuid.UUID, body: RebaselineIn, ctx: Writer, db: DB, today: Today
) -> MilestoneOut:
    """Accept the current forecast as the new committed plan. Always audited with a reason."""
    m = get_scoped(db, ctx, Milestone, milestone_id)
    if m.baseline_date == m.planned_date:
        raise bad_request("Baseline already equals the planned date")
    changes = audit.diff(m, {"baseline_date": m.planned_date})
    audit.record(
        db,
        ctx,
        action="rebaseline",
        entity_type="milestone",
        entity_id=m.id,
        project_id=m.project_id,
        summary=f"Re-baselined '{m.name}' to {m.planned_date.isoformat()}: {body.reason}",
        changes=changes | {"reason": {"from": None, "to": body.reason}},
    )
    return milestones_out(db, ctx, [m], today)[0]


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(milestone_id: uuid.UUID, ctx: Writer, db: DB) -> None:
    m = get_scoped(db, ctx, Milestone, milestone_id)
    m.deleted_at = utcnow()
    audit.record(
        db,
        ctx,
        action="delete",
        entity_type="milestone",
        entity_id=m.id,
        project_id=m.project_id,
        summary=f"Deleted milestone '{m.name}'",
    )


def sprints_out(db: Session, sprints: list[Sprint]) -> list[SprintOut]:
    ids = [s.id for s in sprints]
    totals: dict[uuid.UUID | None, list[int]] = defaultdict(lambda: [0, 0])
    if ids:
        rows = db.execute(
            select(WorkItem.sprint_id, WorkItem.status, WorkItem.story_points).where(
                WorkItem.sprint_id.in_(ids),
                WorkItem.deleted_at.is_(None),
                WorkItem.status != WorkItemStatus.cancelled,
            )
        ).all()
        for sprint_id, item_status, points in rows:
            totals[sprint_id][0] += points or 0
            totals[sprint_id][1] += (points or 0) if item_status == WorkItemStatus.done else 0
    return [
        SprintOut(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            goal=s.goal,
            start_date=s.start_date,
            end_date=s.end_date,
            status=s.status,
            capacity_points=s.capacity_points,
            committed_points=totals[s.id][0],
            done_points=totals[s.id][1],
        )
        for s in sprints
    ]


@router.get("/projects/{project_id}/sprints", response_model=list[SprintOut])
def list_sprints(project_id: uuid.UUID, ctx: CtxDep, db: DB) -> list[SprintOut]:
    project = get_project(db, ctx, project_id)
    sprints = db.scalars(
        select(Sprint).where(Sprint.project_id == project.id).order_by(Sprint.start_date)
    ).all()
    return sprints_out(db, list(sprints))


@router.post(
    "/projects/{project_id}/sprints", response_model=SprintOut, status_code=status.HTTP_201_CREATED
)
def create_sprint(project_id: uuid.UUID, body: SprintCreate, ctx: Writer, db: DB) -> SprintOut:
    project = get_project(db, ctx, project_id)
    if body.end_date < body.start_date:
        raise bad_request("end_date must not be before start_date")
    sprint = Sprint(
        id=uuid.uuid4(), organization_id=ctx.org_id, project_id=project.id, **body.model_dump()
    )
    db.add(sprint)
    db.flush()
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="sprint",
        entity_id=sprint.id,
        project_id=project.id,
        summary=f"Created {sprint.name} ({sprint.start_date} → {sprint.end_date})",
    )
    return sprints_out(db, [sprint])[0]


@router.patch("/sprints/{sprint_id}", response_model=SprintOut)
def update_sprint(sprint_id: uuid.UUID, body: SprintUpdate, ctx: Writer, db: DB) -> SprintOut:
    sprint = get_scoped(db, ctx, Sprint, sprint_id)
    updates = body.model_dump(exclude_unset=True)
    for required in ("name", "start_date", "end_date", "status"):
        if required in updates and updates[required] is None:
            raise bad_request(f"{required} cannot be null")
    if updates.get("end_date", sprint.end_date) < updates.get("start_date", sprint.start_date):
        raise bad_request("end_date must not be before start_date")
    changes = audit.diff(sprint, updates)
    if changes:
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="sprint",
            entity_id=sprint.id,
            project_id=sprint.project_id,
            summary=f"Updated {sprint.name}: {', '.join(changes)}",
            changes=changes,
        )
    return sprints_out(db, [sprint])[0]
