"""Audit writer. Called inside the request transaction, so a mutation and its audit
record either both persist or neither does."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.models import AuditEvent, Project
from app.models.base import utcnow
from app.models.enums import ActorType


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def diff(obj: Any, updates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Apply `updates` to `obj` and return only the fields that actually changed."""
    changes: dict[str, dict[str, Any]] = {}
    for field, new in updates.items():
        old = getattr(obj, field)
        if old != new:
            changes[field] = {"from": _jsonable(old), "to": _jsonable(new)}
            setattr(obj, field, new)
    return changes


def record(
    db: Session,
    ctx: Ctx,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    summary: str,
    project_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
    actor_type: ActorType = ActorType.user,
    actor_label: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=ctx.org_id,
        actor_type=actor_type,
        actor_user_id=ctx.user.id if actor_type == ActorType.user else None,
        actor_label=actor_label or ctx.user.name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        summary=summary,
        changes=_jsonable(changes or {}),
        request_id=ctx.request_id,
    )
    db.add(event)
    if project_id is not None:
        project = db.get(Project, project_id)
        if project is not None:
            project.last_activity_at = utcnow()
    return event
