import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.api.scoped import (
    ensure_in_project,
    ensure_member,
    get_project,
    get_scoped,
    project_keys,
    work_item_out,
)
from app.core import audit
from app.core.deps import DB, Ctx, CtxDep, Writer
from app.core.errors import bad_request, conflict, not_found
from app.models import AuditEvent, Milestone, Sprint, WorkItem, WorkItemLink
from app.models.base import utcnow
from app.models.enums import WORK_ITEM_LEVEL, LinkType, WorkItemStatus, WorkItemType
from app.schemas import (
    AuditOut,
    LinkCreate,
    LinkedItem,
    LinkOut,
    WorkItemCreate,
    WorkItemDetail,
    WorkItemOut,
    WorkItemUpdate,
)
from app.services.graph import cycle_if_added

router = APIRouter(tags=["work items"])


def _validate_parent(
    db: Session,
    ctx: Ctx,
    item_type: WorkItemType,
    parent_id: uuid.UUID | None,
    project_id: uuid.UUID,
) -> None:
    parent = ensure_in_project(db, ctx, WorkItem, parent_id, project_id)
    if parent is not None and WORK_ITEM_LEVEL[parent.type] >= WORK_ITEM_LEVEL[item_type]:
        raise bad_request(f"A {item_type.value} cannot be placed under a {parent.type.value}")


def _apply_status_side_effects(item: WorkItem, updates: dict[str, Any]) -> None:
    new_status = updates.get("status")
    if new_status is None or new_status == item.status:
        return
    if new_status == WorkItemStatus.done:
        updates["completed_at"] = datetime.now(UTC)
    elif item.status == WorkItemStatus.done:
        updates["completed_at"] = None


@router.get("/projects/{project_id}/work-items", response_model=list[WorkItemOut])
def list_work_items(
    project_id: uuid.UUID,
    ctx: CtxDep,
    db: DB,
    status_: Annotated[list[WorkItemStatus] | None, Query(alias="status")] = None,
    type_: Annotated[list[WorkItemType] | None, Query(alias="type")] = None,
    sprint_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    milestone_id: uuid.UUID | None = None,
) -> list[WorkItemOut]:
    project = get_project(db, ctx, project_id)
    query = select(WorkItem).where(
        WorkItem.organization_id == ctx.org_id,
        WorkItem.project_id == project.id,
        WorkItem.deleted_at.is_(None),
    )
    if status_:
        query = query.where(WorkItem.status.in_(status_))
    if type_:
        query = query.where(WorkItem.type.in_(type_))
    if sprint_id:
        query = query.where(WorkItem.sprint_id == sprint_id)
    if assignee_id:
        query = query.where(WorkItem.assignee_id == assignee_id)
    if milestone_id:
        query = query.where(WorkItem.milestone_id == milestone_id)
    items = db.scalars(query.order_by(WorkItem.rank, WorkItem.number)).all()
    return [work_item_out(w, project.key) for w in items]


@router.post(
    "/projects/{project_id}/work-items",
    response_model=WorkItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_work_item(
    project_id: uuid.UUID, body: WorkItemCreate, ctx: Writer, db: DB
) -> WorkItemOut:
    project = get_project(db, ctx, project_id, lock=True)
    _validate_parent(db, ctx, body.type, body.parent_id, project.id)
    ensure_member(db, ctx, body.assignee_id, "assignee_id")
    ensure_in_project(db, ctx, Sprint, body.sprint_id, project.id)
    ensure_in_project(db, ctx, Milestone, body.milestone_id, project.id)
    if body.start_date and body.due_date and body.due_date < body.start_date:
        raise bad_request("due_date must not be before start_date")

    max_rank = db.scalar(select(func.max(WorkItem.rank)).where(WorkItem.project_id == project.id))
    item = WorkItem(
        id=uuid.uuid4(),
        organization_id=ctx.org_id,
        project_id=project.id,
        number=project.next_item_number,
        reporter_id=ctx.user.id,
        rank=(max_rank or 0.0) + 1.0,
        **body.model_dump(exclude={"acceptance_criteria"}),
        acceptance_criteria=[c.model_dump() for c in body.acceptance_criteria],
    )
    if item.status == WorkItemStatus.done:
        item.completed_at = datetime.now(UTC)
    project.next_item_number += 1
    db.add(item)
    db.flush()
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="work_item",
        entity_id=item.id,
        project_id=project.id,
        summary=f"Created {item.type.value} {project.key}-{item.number}: {item.title}",
    )
    return work_item_out(item, project.key)


@router.get("/work-items/{item_id}", response_model=WorkItemDetail)
def get_work_item(item_id: uuid.UUID, ctx: CtxDep, db: DB) -> WorkItemDetail:
    item = get_scoped(db, ctx, WorkItem, item_id)
    keys = project_keys(db, ctx)
    links = db.scalars(
        select(WorkItemLink).where(
            WorkItemLink.organization_id == ctx.org_id,
            or_(WorkItemLink.source_id == item.id, WorkItemLink.target_id == item.id),
        )
    ).all()
    other_ids = {lk.target_id if lk.source_id == item.id else lk.source_id for lk in links}
    others = {
        w.id: w
        for w in db.scalars(
            select(WorkItem).where(WorkItem.id.in_(other_ids), WorkItem.deleted_at.is_(None))
        )
    }
    linked = []
    for lk in links:
        outgoing = lk.source_id == item.id
        other = others.get(lk.target_id if outgoing else lk.source_id)
        if other is not None:
            linked.append(
                LinkedItem(
                    link_id=lk.id,
                    type=lk.type,
                    direction="outgoing" if outgoing else "incoming",
                    item=work_item_out(other, keys[other.project_id]),
                )
            )
    children = db.scalars(
        select(WorkItem)
        .where(WorkItem.parent_id == item.id, WorkItem.deleted_at.is_(None))
        .order_by(WorkItem.rank, WorkItem.number)
    ).all()
    history = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.organization_id == ctx.org_id,
            AuditEvent.entity_type == "work_item",
            AuditEvent.entity_id == item.id,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(50)
    ).all()
    base = work_item_out(item, keys[item.project_id])
    return WorkItemDetail(
        **base.model_dump(),
        links=linked,
        children=[work_item_out(c, keys[c.project_id]) for c in children],
        history=[AuditOut.model_validate(h) for h in history],
    )


@router.patch("/work-items/{item_id}", response_model=WorkItemOut)
def update_work_item(item_id: uuid.UUID, body: WorkItemUpdate, ctx: Writer, db: DB) -> WorkItemOut:
    item = get_scoped(db, ctx, WorkItem, item_id)
    project = get_project(db, ctx, item.project_id)
    updates = body.model_dump(exclude_unset=True)
    if "acceptance_criteria" in updates and updates["acceptance_criteria"] is not None:
        updates["acceptance_criteria"] = [c.model_dump() for c in body.acceptance_criteria or []]
    for nullable_list in ("acceptance_criteria", "labels"):
        if nullable_list in updates and updates[nullable_list] is None:
            updates[nullable_list] = []
    for required in ("type", "title", "status", "priority", "rank"):
        if required in updates and updates[required] is None:
            raise bad_request(f"{required} cannot be null")

    new_type = updates.get("type", item.type)
    new_parent = updates.get("parent_id", item.parent_id)
    if "type" in updates or "parent_id" in updates:
        if new_parent == item.id:
            raise bad_request("An item cannot be its own parent")
        _validate_parent(db, ctx, new_type, new_parent, project.id)
        # Children must still sit below the (possibly changed) type.
        child_types = db.scalars(
            select(WorkItem.type).where(
                WorkItem.parent_id == item.id, WorkItem.deleted_at.is_(None)
            )
        ).all()
        if any(WORK_ITEM_LEVEL[t] <= WORK_ITEM_LEVEL[new_type] for t in child_types):
            raise bad_request(f"Existing children cannot sit under a {new_type.value}")
    if "assignee_id" in updates:
        ensure_member(db, ctx, updates["assignee_id"], "assignee_id")
    if "sprint_id" in updates:
        ensure_in_project(db, ctx, Sprint, updates["sprint_id"], project.id)
    if "milestone_id" in updates:
        ensure_in_project(db, ctx, Milestone, updates["milestone_id"], project.id)
    start = updates.get("start_date", item.start_date)
    due = updates.get("due_date", item.due_date)
    if start and due and due < start:
        raise bad_request("due_date must not be before start_date")

    _apply_status_side_effects(item, updates)
    changes = audit.diff(item, updates)
    changes.pop("completed_at", None)
    if changes:
        if set(changes) == {"rank"}:
            summary = f"Reordered {project.key}-{item.number}"
        elif "status" in changes:
            summary = (
                f"Moved {project.key}-{item.number} from {changes['status']['from']} "
                f"to {changes['status']['to']}"
            )
        else:
            summary = f"Updated {project.key}-{item.number}: {', '.join(changes)}"
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="work_item",
            entity_id=item.id,
            project_id=project.id,
            summary=summary,
            changes=changes,
        )
    return work_item_out(item, project.key)


@router.delete("/work-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_item(item_id: uuid.UUID, ctx: Writer, db: DB) -> None:
    item = get_scoped(db, ctx, WorkItem, item_id)
    project = get_project(db, ctx, item.project_id)
    item.deleted_at = utcnow()
    # Children are re-parented to the deleted item's parent so nothing becomes orphaned.
    db.execute(
        update(WorkItem).where(WorkItem.parent_id == item.id).values(parent_id=item.parent_id)
    )
    audit.record(
        db,
        ctx,
        action="delete",
        entity_type="work_item",
        entity_id=item.id,
        project_id=project.id,
        summary=f"Deleted {project.key}-{item.number}: {item.title}",
    )


@router.get("/projects/{project_id}/links", response_model=list[LinkOut])
def list_project_links(project_id: uuid.UUID, ctx: CtxDep, db: DB) -> list[WorkItemLink]:
    project = get_project(db, ctx, project_id)
    ids = select(WorkItem.id).where(
        WorkItem.project_id == project.id, WorkItem.deleted_at.is_(None)
    )
    return list(
        db.scalars(
            select(WorkItemLink).where(
                WorkItemLink.organization_id == ctx.org_id,
                or_(WorkItemLink.source_id.in_(ids), WorkItemLink.target_id.in_(ids)),
            )
        )
    )


@router.post(
    "/work-items/{item_id}/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED
)
def create_link(item_id: uuid.UUID, body: LinkCreate, ctx: Writer, db: DB) -> WorkItemLink:
    source = get_scoped(db, ctx, WorkItem, item_id)
    target = get_scoped(db, ctx, WorkItem, body.target_id)
    if source.id == target.id:
        raise bad_request("An item cannot depend on itself")
    existing = db.scalar(
        select(WorkItemLink.id).where(
            WorkItemLink.source_id == source.id,
            WorkItemLink.target_id == target.id,
            WorkItemLink.type == body.type,
        )
    )
    if existing:
        raise conflict("This link already exists")
    keys = project_keys(db, ctx)
    if body.type == LinkType.blocks:
        edges = db.execute(
            select(WorkItemLink.source_id, WorkItemLink.target_id).where(
                WorkItemLink.organization_id == ctx.org_id, WorkItemLink.type == LinkType.blocks
            )
        ).all()
        cycle = cycle_if_added([(e[0], e[1]) for e in edges], source.id, target.id)
        if cycle:
            labels = {
                w.id: f"{keys[w.project_id]}-{w.number}"
                for w in db.scalars(select(WorkItem).where(WorkItem.id.in_(cycle)))
            }
            raise conflict(
                "This dependency would create a cycle: " + " → ".join(labels[n] for n in cycle)
            )
    link = WorkItemLink(
        organization_id=ctx.org_id,
        source_id=source.id,
        target_id=target.id,
        type=body.type,
        lag_days=body.lag_days,
        created_at=utcnow(),
    )
    db.add(link)
    db.flush()
    src_label = f"{keys[source.project_id]}-{source.number}"
    tgt_label = f"{keys[target.project_id]}-{target.number}"
    verb = body.type.value.replace("_", " ")
    for item, project_id in ((source, source.project_id), (target, target.project_id)):
        audit.record(
            db,
            ctx,
            action="link",
            entity_type="work_item",
            entity_id=item.id,
            project_id=project_id,
            summary=f"Linked {src_label} {verb} {tgt_label}",
            changes={"link": {"from": None, "to": str(link.id)}},
        )
        if source.project_id == target.project_id:
            break
    return link


@router.delete("/work-item-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: uuid.UUID, ctx: Writer, db: DB) -> None:
    link = db.get(WorkItemLink, link_id)
    if link is None or link.organization_id != ctx.org_id:
        raise not_found("Link")
    source = db.get(WorkItem, link.source_id)
    target = db.get(WorkItem, link.target_id)
    keys = project_keys(db, ctx)
    db.delete(link)
    if source and target:
        audit.record(
            db,
            ctx,
            action="unlink",
            entity_type="work_item",
            entity_id=source.id,
            project_id=source.project_id,
            summary=f"Removed link {keys[source.project_id]}-{source.number} "
            f"{link.type.value.replace('_', ' ')} {keys[target.project_id]}-{target.number}",
        )
