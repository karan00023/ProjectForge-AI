import uuid
from dataclasses import asdict
from datetime import timedelta

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.scoped import ensure_member, get_project
from app.core import audit
from app.core.deps import DB, Admin, Ctx, CtxDep, Today, Writer
from app.core.errors import bad_request, conflict
from app.models import Membership, Milestone, Project, User, WorkItem
from app.models.base import utcnow
from app.models.enums import WorkItemStatus, WorkItemType
from app.schemas import (
    MemberOut,
    ProjectCreate,
    ProjectHealth,
    ProjectOut,
    ProjectSummary,
    ProjectTemplate,
    ProjectUpdate,
    UserOut,
)
from app.services import health
from app.services.templates import TEMPLATES

router = APIRouter(tags=["projects"])


def summarize(db: Session, ctx: Ctx, projects: list[Project], today: Today) -> list[ProjectSummary]:
    results = health.evaluate(db, ctx.org_id, projects, today)
    return [
        ProjectSummary(
            **ProjectOut.model_validate(p).model_dump(),
            health=ProjectHealth.model_validate(asdict(results[p.id])),
        )
        for p in projects
    ]


@router.get("/org/members", response_model=list[MemberOut])
def list_members(ctx: CtxDep, db: DB) -> list[MemberOut]:
    rows = db.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == ctx.org_id)
        .order_by(User.name)
    ).all()
    return [MemberOut(user=UserOut.model_validate(u), role=r) for u, r in rows]


@router.get("/project-templates", response_model=list[ProjectTemplate])
def list_templates(ctx: CtxDep) -> list[ProjectTemplate]:
    return [
        ProjectTemplate(
            id=t.id,
            name=t.name,
            description=t.description,
            kind=t.kind,
            methodology=t.methodology,
            epics=list(t.epics),
            milestones=[m for m, _ in t.milestones],
        )
        for t in TEMPLATES.values()
    ]


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects(ctx: CtxDep, db: DB, today: Today) -> list[ProjectSummary]:
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.organization_id == ctx.org_id, Project.deleted_at.is_(None))
            .order_by(Project.name)
        )
    )
    return summarize(db, ctx, projects, today)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, ctx: Writer, db: DB, today: Today) -> Project:
    if body.start_date and body.target_date and body.target_date < body.start_date:
        raise bad_request("target_date must not be before start_date")
    duplicate = db.scalar(
        select(Project.id).where(
            Project.organization_id == ctx.org_id,
            Project.key == body.key,
            Project.deleted_at.is_(None),
        )
    )
    if duplicate:
        raise conflict(f"Project key {body.key} is already in use")
    ensure_member(db, ctx, body.owner_id, "owner_id")
    template = None
    if body.template:
        template = TEMPLATES.get(body.template)
        if template is None:
            raise bad_request(f"Unknown template '{body.template}'")

    data = body.model_dump(exclude={"template"})
    project = Project(id=uuid.uuid4(), organization_id=ctx.org_id, wip_limits={}, **data)
    project.owner_id = body.owner_id or ctx.user.id
    if template:
        project.kind = template.kind
        project.methodology = template.methodology
    db.add(project)
    db.flush()

    if template:
        start = body.start_date or today
        for i, name in enumerate(template.epics):
            db.add(
                WorkItem(
                    organization_id=ctx.org_id,
                    project_id=project.id,
                    number=project.next_item_number,
                    type=WorkItemType.epic,
                    title=name,
                    status=WorkItemStatus.backlog,
                    rank=float(i),
                    reporter_id=ctx.user.id,
                    acceptance_criteria=[],
                    labels=[],
                )
            )
            project.next_item_number += 1
        for name, offset in template.milestones:
            when = start + timedelta(days=offset)
            db.add(
                Milestone(
                    organization_id=ctx.org_id,
                    project_id=project.id,
                    name=name,
                    baseline_date=when,
                    planned_date=when,
                    owner_id=project.owner_id,
                )
            )
    audit.record(
        db,
        ctx,
        action="create",
        entity_type="project",
        entity_id=project.id,
        project_id=project.id,
        summary=f"Created project {project.key} — {project.name}"
        + (f" from template '{template.name}'" if template else ""),
    )
    return project


@router.get("/projects/{project_id}", response_model=ProjectSummary)
def get_project_detail(project_id: uuid.UUID, ctx: CtxDep, db: DB, today: Today) -> ProjectSummary:
    return summarize(db, ctx, [get_project(db, ctx, project_id)], today)[0]


@router.get("/projects/{project_id}/health", response_model=ProjectHealth)
def get_project_health(project_id: uuid.UUID, ctx: CtxDep, db: DB, today: Today) -> ProjectHealth:
    project = get_project(db, ctx, project_id)
    return ProjectHealth.model_validate(
        asdict(health.evaluate(db, ctx.org_id, [project], today)[project.id])
    )


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, body: ProjectUpdate, ctx: Writer, db: DB) -> Project:
    project = get_project(db, ctx, project_id)
    updates = body.model_dump(exclude_unset=True)
    if "owner_id" in updates:
        ensure_member(db, ctx, updates["owner_id"], "owner_id")
    if "wip_limits" in updates and updates["wip_limits"] is not None:
        updates["wip_limits"] = {str(k): v for k, v in updates["wip_limits"].items()}
    start = updates.get("start_date", project.start_date)
    target = updates.get("target_date", project.target_date)
    if start and target and target < start:
        raise bad_request("target_date must not be before start_date")
    changes = audit.diff(project, updates)
    if changes:
        audit.record(
            db,
            ctx,
            action="update",
            entity_type="project",
            entity_id=project.id,
            project_id=project.id,
            summary=f"Updated {project.key}: {', '.join(changes)}",
            changes=changes,
        )
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, ctx: Admin, db: DB) -> None:
    project = get_project(db, ctx, project_id)
    project.deleted_at = utcnow()
    audit.record(
        db,
        ctx,
        action="delete",
        entity_type="project",
        entity_id=project.id,
        project_id=project.id,
        summary=f"Deleted project {project.key} — {project.name} (soft delete)",
    )
