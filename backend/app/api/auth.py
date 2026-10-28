from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, select

from app.config import get_settings
from app.core.deps import DB, CtxDep
from app.core.security import (
    SlidingWindowLimiter,
    hash_token,
    new_session_token,
    verify_password,
)
from app.models import Membership, Organization, User, UserSession
from app.models.enums import ROLE_RANK
from app.schemas import (
    DemoLoginIn,
    DemoPersona,
    LoginIn,
    MembershipOut,
    MeOut,
    OrgOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
login_limiter = SlidingWindowLimiter(
    _settings.login_rate_limit_attempts, _settings.login_rate_limit_window_seconds
)


def _start_session(db: DB, user: User, request: Request, response: Response) -> None:
    settings = get_settings()
    token = new_session_token()
    now = datetime.now(UTC)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(hours=settings.session_ttl_hours),
            user_agent=(request.headers.get("user-agent") or "")[:255],
        )
    )
    # Purge this user's expired sessions opportunistically.
    db.execute(
        delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now)
    )
    # Demo personas keep their seeded "last visit" so every reviewer sees the same briefing.
    if user.last_seen_at is not None and not user.is_demo:
        user.previous_seen_at = user.last_seen_at
    user.last_seen_at = now
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(body: LoginIn, request: Request, response: Response, db: DB) -> None:
    email = body.email.lower()
    client = request.client.host if request.client else "unknown"
    if not login_limiter.hit(f"{client}:{email}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts; try later")
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    _start_session(db, user, request, response)


@router.get("/demo-personas", response_model=list[DemoPersona])
def demo_personas(db: DB) -> list[DemoPersona]:
    if not get_settings().demo_mode:
        return []
    rows = db.execute(
        select(User, Membership, Organization)
        .join(Membership, Membership.user_id == User.id)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(User.is_demo.is_(True), Organization.is_demo.is_(True))
    ).all()
    rows = sorted(rows, key=lambda r: (r[2].name, -ROLE_RANK[r[1].role], r[0].name))
    return [
        DemoPersona(
            email=u.email,
            name=u.name,
            title=u.title,
            avatar_color=u.avatar_color,
            role=m.role,
            organization=o.name,
        )
        for u, m, o in rows
    ]


@router.post("/demo-login", status_code=status.HTTP_204_NO_CONTENT)
def demo_login(body: DemoLoginIn, request: Request, response: Response, db: DB) -> None:
    if not get_settings().demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demo mode is disabled")
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_demo.is_(True)))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown demo persona")
    _start_session(db, user, request, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DB) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeOut)
def me(ctx: CtxDep, db: DB) -> MeOut:
    memberships = db.scalars(
        select(Membership)
        .where(Membership.user_id == ctx.user.id)
        .order_by(Membership.created_at, Membership.id)
    ).all()
    return MeOut(
        user=UserOut.model_validate(ctx.user),
        organization=OrgOut.model_validate(ctx.org),
        role=ctx.role,
        memberships=[
            MembershipOut(organization=OrgOut.model_validate(m.organization), role=m.role)
            for m in memberships
        ],
        previous_seen_at=ctx.user.previous_seen_at,
        demo_mode=get_settings().demo_mode,
    )
