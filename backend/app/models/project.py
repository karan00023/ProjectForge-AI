import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SoftDeleteMixin, TenantMixin, TimestampMixin, str_enum
from app.models.enums import (
    DecisionStatus,
    LifecyclePhase,
    LinkType,
    Methodology,
    MilestoneStatus,
    Priority,
    ProjectKind,
    ProjectStatus,
    RaidStatus,
    RaidType,
    SprintStatus,
    WorkItemStatus,
    WorkItemType,
)


def _fts(*cols: str) -> Computed:
    joined = " || ' ' || ".join(f"coalesce({c}, '')" for c in cols)
    return Computed(f"to_tsvector('english', {joined})", persisted=True)


class Portfolio(IdMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)


class Program(IdMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "programs"

    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)


class Project(IdMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "uq_projects_org_key_live",
            "organization_id",
            "key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_projects_search", "search_vector", postgresql_using="gin"),
    )

    program_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="SET NULL"), index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL")
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    key: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        str_enum(ProjectStatus, "project_status"), default=ProjectStatus.active
    )
    methodology: Mapped[Methodology] = mapped_column(
        str_enum(Methodology, "methodology"), default=Methodology.scrum
    )
    phase: Mapped[LifecyclePhase] = mapped_column(
        str_enum(LifecyclePhase, "lifecycle_phase"), default=LifecyclePhase.planning
    )
    kind: Mapped[ProjectKind] = mapped_column(
        str_enum(ProjectKind, "project_kind"), default=ProjectKind.general
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    target_date: Mapped[date | None] = mapped_column(Date)
    # Board WIP limits per status, e.g. {"in_progress": 5}. Exceeding is a warning, not a block.
    wip_limits: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    next_item_number: Mapped[int] = mapped_column(Integer, default=1)
    next_raid_number: Mapped[int] = mapped_column(Integer, default=1)
    next_decision_number: Mapped[int] = mapped_column(Integer, default=1)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[Any] = mapped_column(TSVECTOR, _fts("key", "name", "description"))

    owner = relationship("User", foreign_keys=[owner_id])


class Sprint(IdMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "sprints"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="dates_ordered"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    goal: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[SprintStatus] = mapped_column(
        str_enum(SprintStatus, "sprint_status"), default=SprintStatus.planned
    )
    capacity_points: Mapped[int | None] = mapped_column(Integer)


class Milestone(IdMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    __tablename__ = "milestones"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    # baseline_date is the committed plan; it only changes through an explicit, audited re-baseline.
    baseline_date: Mapped[date] = mapped_column(Date)
    planned_date: Mapped[date] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[MilestoneStatus] = mapped_column(
        str_enum(MilestoneStatus, "milestone_status"), default=MilestoneStatus.open
    )


class WorkItem(IdMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint("project_id", "number"),
        CheckConstraint("story_points IS NULL OR story_points >= 0", name="points_non_negative"),
        Index("ix_work_items_project_status", "project_id", "status"),
        Index("ix_work_items_search", "search_vector", postgresql_using="gin"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="SET NULL"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    type: Mapped[WorkItemType] = mapped_column(str_enum(WorkItemType, "work_item_type"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WorkItemStatus] = mapped_column(
        str_enum(WorkItemStatus, "work_item_status"), default=WorkItemStatus.backlog
    )
    priority: Mapped[Priority] = mapped_column(
        str_enum(Priority, "priority"), default=Priority.medium
    )
    story_points: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sprints.id", ondelete="SET NULL"), index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL"), index=True
    )
    # [{"id": "...", "text": "...", "format": "plain"|"gherkin"}]
    acceptance_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    labels: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Fractional rank keeps manual ordering cheap (insert between neighbours without renumbering).
    rank: Mapped[float] = mapped_column(Float, default=0.0)
    search_vector: Mapped[Any] = mapped_column(TSVECTOR, _fts("title", "description"))

    project: Mapped[Project] = relationship()


class WorkItemLink(IdMixin, TenantMixin, Base):
    """Directed relationship. For `blocks`: source must finish before target can finish."""

    __tablename__ = "work_item_links"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "type"),
        CheckConstraint("source_id <> target_id", name="no_self_link"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[LinkType] = mapped_column(str_enum(LinkType, "link_type"))
    lag_days: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RaidItem(IdMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    __tablename__ = "raid_items"
    __table_args__ = (
        UniqueConstraint("project_id", "number"),
        CheckConstraint("probability IS NULL OR probability BETWEEN 1 AND 5", name="prob_range"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="impact_range"),
        Index("ix_raid_items_search", "search_vector", postgresql_using="gin"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    type: Mapped[RaidType] = mapped_column(str_enum(RaidType, "raid_type"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RaidStatus] = mapped_column(
        str_enum(RaidStatus, "raid_status"), default=RaidStatus.open
    )
    priority: Mapped[Priority] = mapped_column(
        str_enum(Priority, "priority"), default=Priority.medium
    )
    # Probability applies to risks; issues have already happened (probability is NULL).
    probability: Mapped[int | None] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer, default=3)
    score: Mapped[int | None] = mapped_column(
        Integer, Computed("probability * impact", persisted=True)
    )
    mitigation: Mapped[str | None] = mapped_column(Text)
    contingency: Mapped[str | None] = mapped_column(Text)
    escalation_trigger: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL")
    )
    search_vector: Mapped[Any] = mapped_column(TSVECTOR, _fts("title", "description", "mitigation"))

    work_items: Mapped[list[WorkItem]] = relationship(secondary="raid_item_work_items")


class RaidItemWorkItem(Base):
    __tablename__ = "raid_item_work_items"

    raid_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raid_items.id", ondelete="CASCADE"), primary_key=True
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True
    )


class Decision(IdMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    __tablename__ = "decisions"
    __table_args__ = (
        UniqueConstraint("project_id", "number"),
        Index("ix_decisions_search", "search_vector", postgresql_using="gin"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    context: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    # [{"option": "...", "pros": "...", "cons": "..."}]
    alternatives: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    impact: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DecisionStatus] = mapped_column(
        str_enum(DecisionStatus, "decision_status"), default=DecisionStatus.proposed
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="SET NULL")
    )
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, _fts("title", "context", "decision", "rationale")
    )
