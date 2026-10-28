import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.scoped import (
    decision_out,
    ensure_in_project,
    ensure_member,
    get_project,
    get_scoped,
    raid_out,
)
from app.core import audit
from app.core.deps import DB, Ctx, CtxDep, Writer
from app.core.errors import bad_request
from app.models import Decision, Milestone, RaidItem, WorkItem
from app.models.base import utcnow
from app.models.enums import DecisionStatus, RaidStatus, RaidType
from app.schemas import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    RaidCreate,
    RaidOut,
    RaidUpdate,
)

router = APIRouter(tags=["raid & decisions"])


def _work_items(
    db: Session, ctx: Ctx, ids: list[uuid.UUID], project_id: uuid.UUID
) -> list[WorkItem]:
    items = [ensure_in_project(db, ctx, WorkItem, i, project_id) for i in dict.fromkeys(ids)]
    return [i for i in items if i is not None]


# ---------- RAID ----------


@router.get("/projects/{project_id}/raid", response_model=list[RaidOut])
def list_raid(
    project_id: uuid.UUID,
    ctx: CtxDep,
    db: DB,
    type_: Annotated[list[RaidType] | None, Query(alias="type")] = None,
    status_: Annotated[list[RaidStatus] | None, Query(alias="status")] = None,
) -> list[RaidOut]:
    project = get_project(db, ctx, project_id)
    query = select(RaidItem).where(
        RaidItem.organization_id == ctx.org_id,
        RaidItem.project_id == project.id,
        RaidItem.deleted_at.is_(None),
    )
    if type_:
        query = query.where(RaidItem.type.in_(type_))
    if status_:
        query = query.where(RaidItem.status.in_(status_))
    rows = db.scalars(query.order_by(RaidItem.score.desc().nulls_last(), RaidItem.number)).all()
    return [raid_out(r, project.key) for r in rows]


@router.post(
    "/projects/{project_id}/raid", response_model=RaidOut, status_code=status.HTTP_201_CREATED
)
def create_raid(project_id: uuid.UUID, body: RaidCreate, ctx: Writer, db: DB) -> RaidOut:
    project = get_project(db, ctx, project_id, lock=True)
    if body.type == RaidType.risk and body.probability is None:
        raise bad_request("Risks need a probability (1–5)")
    if body.type != RaidType.risk and body.probability is not None:
        raise bad_request("Only risks carry a probability")
    ensure_member(db, ctx, body.owner_id, "owner_id")
    ensure_in_project(db, ctx, Milestone, body.milestone_id, project.id)
    item = RaidItem(
        id=uuid.uuid4(),
        organization_id=ctx.org_id,
        project_id=project.id,
        number=project.next_raid_number,
        **body.model_dump(exclude={"work_item_ids"}),
    )
    item.work_items = _work_items(db, ctx, body.work_item_ids, project.id)
    project.next_raid_number += 1
    db.add(item)
    db.flush()
    db.refresh(item)  # load generated score
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="raid_item",
        entity_id=item.id,
        project_id=project.id,
        summary=f"Logged {item.type.value} {project.key}-R{item.number}: {item.title}",
    )
    return raid_out(item, project.key)


@router.get("/raid/{raid_id}", response_model=RaidOut)
def get_raid(raid_id: uuid.UUID, ctx: CtxDep, db: DB) -> RaidOut:
    item = get_scoped(db, ctx, RaidItem, raid_id)
    return raid_out(item, get_project(db, ctx, item.project_id).key)


@router.patch("/raid/{raid_id}", response_model=RaidOut)
def update_raid(raid_id: uuid.UUID, body: RaidUpdate, ctx: Writer, db: DB) -> RaidOut:
    item = get_scoped(db, ctx, RaidItem, raid_id)
    project = get_project(db, ctx, item.project_id)
    updates = body.model_dump(exclude_unset=True)
    for required in ("title", "status", "priority", "impact"):
        if required in updates and updates[required] is None:
            raise bad_request(f"{required} cannot be null")
    if item.type == RaidType.risk and "probability" in updates and updates["probability"] is None:
        raise bad_request("Risks need a probability (1–5)")
    if item.type != RaidType.risk and updates.get("probability") is not None:
        raise bad_request("Only risks carry a probability")
    if "owner_id" in updates:
        ensure_member(db, ctx, updates["owner_id"], "owner_id")
    if "milestone_id" in updates:
        ensure_in_project(db, ctx, Milestone, updates["milestone_id"], project.id)
    changes = {}
    if "work_item_ids" in updates:
        new_items = _work_items(db, ctx, updates.pop("work_item_ids") or [], project.id)
        old_ids = sorted(str(w.id) for w in item.work_items)
        new_ids = sorted(str(w.id) for w in new_items)
        if old_ids != new_ids:
            item.work_items = new_items
            changes["work_item_ids"] = {"from": old_ids, "to": new_ids}
    changes |= audit.diff(item, updates)
    if changes:
        db.flush()
        db.refresh(item)
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="raid_item",
            entity_id=item.id,
            project_id=project.id,
            summary=f"Updated {project.key}-R{item.number}: {', '.join(changes)}",
            changes=changes,
        )
    return raid_out(item, project.key)


@router.delete("/raid/{raid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_raid(raid_id: uuid.UUID, ctx: Writer, db: DB) -> None:
    item = get_scoped(db, ctx, RaidItem, raid_id)
    project = get_project(db, ctx, item.project_id)
    item.deleted_at = utcnow()
    audit.record(
        db,
        ctx,
        action="delete",
        entity_type="raid_item",
        entity_id=item.id,
        project_id=project.id,
        summary=f"Deleted {project.key}-R{item.number}: {item.title}",
    )


# ---------- decisions ----------


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionOut])
def list_decisions(project_id: uuid.UUID, ctx: CtxDep, db: DB) -> list[DecisionOut]:
    project = get_project(db, ctx, project_id)
    rows = db.scalars(
        select(Decision)
        .where(Decision.project_id == project.id, Decision.deleted_at.is_(None))
        .order_by(Decision.number.desc())
    ).all()
    return [decision_out(d, project.key) for d in rows]


def _mark_decided(d: Decision, ctx: Ctx) -> None:
    d.decided_by_id = ctx.user.id
    d.decided_at = utcnow()


@router.post(
    "/projects/{project_id}/decisions",
    response_model=DecisionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_decision(
    project_id: uuid.UUID, body: DecisionCreate, ctx: Writer, db: DB
) -> DecisionOut:
    project = get_project(db, ctx, project_id, lock=True)
    superseded = ensure_in_project(db, ctx, Decision, body.supersedes_id, project.id)
    d = Decision(
        id=uuid.uuid4(),
        organization_id=ctx.org_id,
        project_id=project.id,
        number=project.next_decision_number,
        **body.model_dump(exclude={"alternatives"}),
        alternatives=[a.model_dump() for a in body.alternatives],
    )
    if d.status in {DecisionStatus.accepted, DecisionStatus.rejected}:
        _mark_decided(d, ctx)
    project.next_decision_number += 1
    db.add(d)
    db.flush()
    if superseded is not None:
        changes = audit.diff(superseded, {"status": DecisionStatus.superseded})
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="decision",
            entity_id=superseded.id,
            project_id=project.id,
            summary=f"{project.key}-D{superseded.number} superseded by {project.key}-D{d.number}",
            changes=changes,
        )
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="decision",
        entity_id=d.id,
        project_id=project.id,
        summary=f"Recorded decision {project.key}-D{d.number} ({d.status.value}): {d.title}",
    )
    return decision_out(d, project.key)


@router.patch("/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(
    decision_id: uuid.UUID, body: DecisionUpdate, ctx: Writer, db: DB
) -> DecisionOut:
    d = get_scoped(db, ctx, Decision, decision_id)
    project = get_project(db, ctx, d.project_id)
    updates = body.model_dump(exclude_unset=True)
    for required in ("title", "decision", "status"):
        if required in updates and updates[required] is None:
            raise bad_request(f"{required} cannot be null")
    if "alternatives" in updates:
        updates["alternatives"] = [a.model_dump() for a in body.alternatives or []]
    changes = audit.diff(d, updates)
    if "status" in changes and d.status in {DecisionStatus.accepted, DecisionStatus.rejected}:
        _mark_decided(d, ctx)
    if changes:
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="decision",
            entity_id=d.id,
            project_id=project.id,
            summary=f"Updated decision {project.key}-D{d.number}: {', '.join(changes)}",
            changes=changes,
        )
    return decision_out(d, project.key)
