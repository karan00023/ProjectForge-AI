"""Request context: who is calling, in which organization, with which role.

Every tenant-scoped endpoint depends on `Ctx`. The organization comes from a verified
membership — never from a request body — so a caller cannot address another tenant.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import forbidden
from app.core.security import hash_token
from app.db import get_db
from app.models import Membership, Organization, User, UserSession
from app.models.enums import ROLE_RANK, Role

DB = Annotated[Session, Depends(get_db)]

# Refresh last_seen_at at most this often; the previous value becomes "since your last visit".
_SEEN_GRANULARITY = timedelta(minutes=30)
_NEW_VISIT_GAP = timedelta(hours=4)


def get_today() -> date:
    """Injectable clock for every 'is this overdue?' decision. Overridden in tests."""
    return datetime.now(UTC).date()


Today = Annotated[date, Depends(get_today)]


@dataclass(frozen=True)
class Ctx:
    user: User
    org: Organization
    role: Role
    request_id: str | None

    @property
    def org_id(self) -> uuid.UUID:
        return self.org.id

    def can(self, minimum: Role) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[minimum]

    def require(self, minimum: Role) -> None:
        if not self.can(minimum):
            raise forbidden()


def get_current_user(request: Request, db: DB) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    now = datetime.now(UTC)
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token), UserSession.expires_at > now
        )
    )
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    if now - session.last_used_at > _SEEN_GRANULARITY:
        session.last_used_at = now
    if user.last_seen_at is None or now - user.last_seen_at > _SEEN_GRANULARITY:
        # A long gap starts a new visit: remember where the previous one ended.
        new_visit = user.last_seen_at is None or now - user.last_seen_at > _NEW_VISIT_GAP
        if new_visit and not user.is_demo:
            user.previous_seen_at = user.last_seen_at
        user.last_seen_at = now
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_ctx(
    request: Request,
    db: DB,
    user: CurrentUser,
    x_org_id: Annotated[str | None, Header()] = None,
) -> Ctx:
    query = (
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at, Membership.id)
    )
    if x_org_id:
        try:
            org_uuid = uuid.UUID(x_org_id)
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found") from None
        query = query.where(Membership.organization_id == org_uuid)
    membership = db.scalars(query).first()
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return Ctx(
        user=user,
        org=membership.organization,
        role=membership.role,
        request_id=getattr(request.state, "request_id", None),
    )


CtxDep = Annotated[Ctx, Depends(get_ctx)]


def require_role(minimum: Role) -> Callable[[Ctx], Ctx]:
    def checker(ctx: CtxDep) -> Ctx:
        ctx.require(minimum)
        return ctx

    return checker


# Writers: anyone who can change project data.
Writer = Annotated[Ctx, Depends(require_role(Role.member))]
Admin = Annotated[Ctx, Depends(require_role(Role.admin))]
