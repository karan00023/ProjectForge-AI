"""Pydantic request/response models. These define the public API contract (OpenAPI)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, StringConstraints

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
    Role,
    SprintStatus,
    WorkItemStatus,
    WorkItemType,
)

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
LongText = Annotated[str, StringConstraints(max_length=20_000)]
ProjectKey = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    StringConstraints(pattern=r"^[A-Z][A-Z0-9]{1,7}$"),
]
Score = Annotated[int, Field(ge=1, le=5)]


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Patch(BaseModel):
    """PATCH bodies: only explicitly provided fields are applied (model_dump(exclude_unset))."""

    model_config = ConfigDict(extra="forbid")


# ---------- auth & org ----------


class LoginIn(BaseModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class DemoLoginIn(BaseModel):
    email: EmailStr


class UserOut(Out):
    id: uuid.UUID
    email: str
    name: str
    title: str | None
    avatar_color: str
    is_demo: bool


class OrgOut(Out):
    id: uuid.UUID
    name: str
    slug: str
    is_demo: bool


class MembershipOut(BaseModel):
    organization: OrgOut
    role: Role


class MeOut(BaseModel):
    user: UserOut
    organization: OrgOut
    role: Role
    memberships: list[MembershipOut]
    previous_seen_at: datetime | None
    demo_mode: bool


class DemoPersona(BaseModel):
    email: str
    name: str
    title: str | None
    avatar_color: str
    role: Role
    organization: str


class MemberOut(BaseModel):
    user: UserOut
    role: Role


# ---------- projects ----------


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: ProjectKey
    name: Name
    description: LongText | None = None
    methodology: Methodology = Methodology.scrum
    phase: LifecyclePhase = LifecyclePhase.planning
    kind: ProjectKind = ProjectKind.general
    status: ProjectStatus = ProjectStatus.active
    start_date: date | None = None
    target_date: date | None = None
    owner_id: uuid.UUID | None = None
    template: str | None = Field(default=None, description="Template id from /project-templates")


class ProjectUpdate(Patch):
    name: Name | None = None
    description: LongText | None = None
    methodology: Methodology | None = None
    phase: LifecyclePhase | None = None
    kind: ProjectKind | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    target_date: date | None = None
    owner_id: uuid.UUID | None = None
    wip_limits: dict[WorkItemStatus, Annotated[int, Field(ge=1, le=99)]] | None = None


class ProjectOut(Out):
    id: uuid.UUID
    key: str
    name: str
    description: str | None
    status: ProjectStatus
    methodology: Methodology
    phase: LifecyclePhase
    kind: ProjectKind
    start_date: date | None
    target_date: date | None
    owner_id: uuid.UUID | None
    wip_limits: dict[str, int]
    last_activity_at: datetime | None
    created_at: datetime


class ProjectTemplate(BaseModel):
    id: str
    name: str
    description: str
    kind: ProjectKind
    methodology: Methodology
    epics: list[str]
    milestones: list[str]


# ---------- health ----------

HealthLevel = Literal["green", "amber", "red"]


class EvidenceRef(BaseModel):
    entity_type: Literal["work_item", "milestone", "raid_item", "project"]
    id: uuid.UUID
    label: str


class HealthSignal(BaseModel):
    code: str
    level: Literal["amber", "red"]
    message: str
    evidence: list[EvidenceRef]


class ProgressOut(BaseModel):
    items_total: int
    items_done: int
    points_total: int
    points_done: int
    unestimated_items: int


class ProjectHealth(BaseModel):
    project_id: uuid.UUID
    level: HealthLevel
    signals: list[HealthSignal]
    progress: ProgressOut
    evaluated_on: date
    rules_version: str


class ProjectSummary(ProjectOut):
    health: ProjectHealth


# ---------- work items ----------


class AcceptanceCriterion(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    format: Literal["plain", "gherkin"] = "plain"


class WorkItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: WorkItemType
    title: Title
    description: LongText | None = None
    status: WorkItemStatus = WorkItemStatus.backlog
    priority: Priority = Priority.medium
    story_points: Annotated[int, Field(ge=0, le=100)] | None = None
    start_date: date | None = None
    due_date: date | None = None
    parent_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    acceptance_criteria: list[AcceptanceCriterion] = []
    labels: list[Annotated[str, StringConstraints(max_length=40)]] = []


class WorkItemUpdate(Patch):
    type: WorkItemType | None = None
    title: Title | None = None
    description: LongText | None = None
    status: WorkItemStatus | None = None
    priority: Priority | None = None
    story_points: Annotated[int, Field(ge=0, le=100)] | None = None
    start_date: date | None = None
    due_date: date | None = None
    parent_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    acceptance_criteria: list[AcceptanceCriterion] | None = None
    labels: list[Annotated[str, StringConstraints(max_length=40)]] | None = None
    rank: float | None = None


class WorkItemOut(Out):
    id: uuid.UUID
    project_id: uuid.UUID
    key: str
    number: int
    type: WorkItemType
    title: str
    description: str | None
    status: WorkItemStatus
    priority: Priority
    story_points: int | None
    start_date: date | None
    due_date: date | None
    completed_at: datetime | None
    parent_id: uuid.UUID | None
    assignee_id: uuid.UUID | None
    reporter_id: uuid.UUID | None
    sprint_id: uuid.UUID | None
    milestone_id: uuid.UUID | None
    acceptance_criteria: list[dict[str, Any]]
    labels: list[str]
    rank: float
    created_at: datetime
    updated_at: datetime


class LinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: uuid.UUID
    type: LinkType = LinkType.blocks
    lag_days: Annotated[int, Field(ge=0, le=365)] = 0


class LinkOut(Out):
    id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    type: LinkType
    lag_days: int


class LinkedItem(BaseModel):
    link_id: uuid.UUID
    type: LinkType
    direction: Literal["outgoing", "incoming"]
    item: WorkItemOut


class WorkItemDetail(WorkItemOut):
    links: list[LinkedItem]
    children: list[WorkItemOut]
    history: list["AuditOut"]


# ---------- milestones & sprints ----------


class MilestoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: LongText | None = None
    planned_date: date
    owner_id: uuid.UUID | None = None


class MilestoneUpdate(Patch):
    name: Name | None = None
    description: LongText | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    status: MilestoneStatus | None = None
    owner_id: uuid.UUID | None = None


class RebaselineIn(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class MilestoneOut(Out):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    baseline_date: date
    planned_date: date
    actual_date: date | None
    status: MilestoneStatus
    owner_id: uuid.UUID | None
    variance_working_days: int
    overdue: bool
    deliverables_total: int
    deliverables_done: int


class SprintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    goal: LongText | None = None
    start_date: date
    end_date: date
    capacity_points: Annotated[int, Field(ge=0, le=1000)] | None = None
    status: SprintStatus = SprintStatus.planned


class SprintUpdate(Patch):
    name: Name | None = None
    goal: LongText | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity_points: Annotated[int, Field(ge=0, le=1000)] | None = None
    status: SprintStatus | None = None


class SprintOut(Out):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    goal: str | None
    start_date: date
    end_date: date
    status: SprintStatus
    capacity_points: int | None
    committed_points: int
    done_points: int


# ---------- RAID & decisions ----------


class RaidCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RaidType
    title: Title
    description: LongText | None = None
    status: RaidStatus = RaidStatus.open
    priority: Priority = Priority.medium
    probability: Score | None = None
    impact: Score = 3
    mitigation: LongText | None = None
    contingency: LongText | None = None
    escalation_trigger: LongText | None = None
    evidence: LongText | None = None
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    milestone_id: uuid.UUID | None = None
    work_item_ids: list[uuid.UUID] = []


class RaidUpdate(Patch):
    title: Title | None = None
    description: LongText | None = None
    status: RaidStatus | None = None
    priority: Priority | None = None
    probability: Score | None = None
    impact: Score | None = None
    mitigation: LongText | None = None
    contingency: LongText | None = None
    escalation_trigger: LongText | None = None
    evidence: LongText | None = None
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    milestone_id: uuid.UUID | None = None
    work_item_ids: list[uuid.UUID] | None = None


class RaidOut(Out):
    id: uuid.UUID
    project_id: uuid.UUID
    key: str
    number: int
    type: RaidType
    title: str
    description: str | None
    status: RaidStatus
    priority: Priority
    probability: int | None
    impact: int
    score: int | None
    mitigation: str | None
    contingency: str | None
    escalation_trigger: str | None
    evidence: str | None
    owner_id: uuid.UUID | None
    due_date: date | None
    milestone_id: uuid.UUID | None
    work_item_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class Alternative(BaseModel):
    option: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    pros: Annotated[str, StringConstraints(max_length=2000)] = ""
    cons: Annotated[str, StringConstraints(max_length=2000)] = ""


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    context: LongText | None = None
    decision: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)
    ]
    rationale: LongText | None = None
    alternatives: list[Alternative] = []
    impact: LongText | None = None
    status: DecisionStatus = DecisionStatus.proposed
    supersedes_id: uuid.UUID | None = None


class DecisionUpdate(Patch):
    title: Title | None = None
    context: LongText | None = None
    decision: LongText | None = None
    rationale: LongText | None = None
    alternatives: list[Alternative] | None = None
    impact: LongText | None = None
    status: DecisionStatus | None = None


class DecisionOut(Out):
    id: uuid.UUID
    project_id: uuid.UUID
    key: str
    number: int
    title: str
    context: str | None
    decision: str
    rationale: str | None
    alternatives: list[dict[str, Any]]
    impact: str | None
    status: DecisionStatus
    decided_by_id: uuid.UUID | None
    decided_at: datetime | None
    supersedes_id: uuid.UUID | None
    created_at: datetime


# ---------- activity, search, dashboard ----------


class AuditOut(Out):
    id: uuid.UUID
    created_at: datetime
    actor_type: str
    actor_user_id: uuid.UUID | None
    actor_label: str
    action: str
    entity_type: str
    entity_id: uuid.UUID
    project_id: uuid.UUID | None
    summary: str
    changes: dict[str, Any]


class SearchHit(BaseModel):
    entity_type: Literal["project", "work_item", "raid_item", "decision"]
    id: uuid.UUID
    project_id: uuid.UUID
    label: str
    title: str
    snippet: str | None
    rank: float


class Kpi(BaseModel):
    id: str
    label: str
    value: float | None
    display: str
    definition: str
    numerator: int | None = None
    denominator: int | None = None


class DeadlineOut(BaseModel):
    entity_type: Literal["milestone", "work_item"]
    id: uuid.UUID
    project_id: uuid.UUID
    project_key: str
    label: str
    title: str
    date: date
    overdue: bool


class DashboardOut(BaseModel):
    evaluated_on: date
    kpis: list[Kpi]
    projects: list[ProjectSummary]
    critical_risks: list[RaidOut]
    blocked_items: list[WorkItemOut]
    deadlines: list[DeadlineOut]
    pending_decisions: list[DecisionOut]
    recent_activity: list[AuditOut]
    changes_since_last_visit: int


WorkItemDetail.model_rebuild()
