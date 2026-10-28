"""Tenant-scoped lookups and serializers shared by routers.

Every fetch filters by the caller's organization and excludes soft-deleted rows; a miss in
either case is reported as 404 so other tenants' ids cannot be probed.
"""

import uuid
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.core.errors import bad_request, not_found
from app.models import (
    Decision,
    Membership,
    Milestone,
    Project,
    RaidItem,
    Sprint,
    WorkItem,
)
from app.schemas import DecisionOut, RaidOut, WorkItemOut

T = TypeVar("T", Project, WorkItem, Milestone, RaidItem, Decision, Sprint)

_LABELS = {
    Project: "Project",
    WorkItem: "Work item",
    Milestone: "Milestone",
    RaidItem: "RAID item",
    Decision: "Decision",
    Sprint: "Sprint",
}


def get_scoped(db: Session, ctx: Ctx, model: type[T], entity_id: uuid.UUID) -> T:
    obj = db.get(model, entity_id)
    if (
        obj is None
        or obj.organization_id != ctx.org_id
        or getattr(obj, "deleted_at", None) is not None
    ):
        raise not_found(_LABELS[model])
    return obj


def get_project(db: Session, ctx: Ctx, project_id: uuid.UUID, *, lock: bool = False) -> Project:
    if lock:
        # Serialises per-project counters (item numbers) across concurrent requests.
        project = db.scalar(
            select(Project)
            .where(Project.id == project_id, Project.organization_id == ctx.org_id)
            .with_for_update()
        )
        if project is None or project.deleted_at is not None:
            raise not_found("Project")
        return project
    return get_scoped(db, ctx, Project, project_id)


def ensure_member(db: Session, ctx: Ctx, user_id: uuid.UUID | None, field: str) -> None:
    """Assignees/owners must belong to the caller's organization."""
    if user_id is None:
        return
    exists = db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.organization_id == ctx.org_id, Membership.user_id == user_id)
    )
    if not exists:
        raise bad_request(f"{field} is not a member of this organization")


def ensure_in_project(
    db: Session, ctx: Ctx, model: type[T], entity_id: uuid.UUID | None, project_id: uuid.UUID
) -> T | None:
    if entity_id is None:
        return None
    obj = get_scoped(db, ctx, model, entity_id)
    if getattr(obj, "project_id", None) != project_id:
        raise bad_request(f"{_LABELS[model]} belongs to a different project")
    return obj


def work_item_out(item: WorkItem, project_key: str) -> WorkItemOut:
    data: dict[str, Any] = {
        f: getattr(item, f) for f in WorkItemOut.model_fields if f != "key" and hasattr(item, f)
    }
    return WorkItemOut(key=f"{project_key}-{item.number}", **data)


def raid_out(item: RaidItem, project_key: str) -> RaidOut:
    data: dict[str, Any] = {
        f: getattr(item, f)
        for f in RaidOut.model_fields
        if f not in {"key", "work_item_ids"} and hasattr(item, f)
    }
    return RaidOut(
        key=f"{project_key}-R{item.number}",
        work_item_ids=[w.id for w in item.work_items],
        **data,
    )


def decision_out(d: Decision, project_key: str) -> DecisionOut:
    data: dict[str, Any] = {
        f: getattr(d, f) for f in DecisionOut.model_fields if f != "key" and hasattr(d, f)
    }
    return DecisionOut(key=f"{project_key}-D{d.number}", **data)


def project_keys(db: Session, ctx: Ctx) -> dict[uuid.UUID, str]:
    rows = db.execute(
        select(Project.id, Project.key).where(Project.organization_id == ctx.org_id)
    ).all()
    return {r.id: r.key for r in rows}
