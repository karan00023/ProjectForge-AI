from enum import StrEnum


class Role(StrEnum):
    viewer = "viewer"
    member = "member"
    admin = "admin"
    owner = "owner"


ROLE_RANK = {Role.viewer: 0, Role.member: 1, Role.admin: 2, Role.owner: 3}


class ProjectStatus(StrEnum):
    proposed = "proposed"
    active = "active"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"


class Methodology(StrEnum):
    scrum = "scrum"
    kanban = "kanban"
    waterfall = "waterfall"
    hybrid = "hybrid"


class LifecyclePhase(StrEnum):
    idea = "idea"
    discovery = "discovery"
    business_case = "business_case"
    planning = "planning"
    requirements = "requirements"
    engineering = "engineering"
    testing = "testing"
    release = "release"
    monitoring = "monitoring"
    closure = "closure"


class ProjectKind(StrEnum):
    general = "general"
    software = "software"
    data_platform = "data_platform"
    ai_product = "ai_product"


class WorkItemType(StrEnum):
    initiative = "initiative"
    epic = "epic"
    feature = "feature"
    story = "story"
    task = "task"
    bug = "bug"
    subtask = "subtask"


# A parent must sit strictly higher in the hierarchy than its child.
WORK_ITEM_LEVEL = {
    WorkItemType.initiative: 0,
    WorkItemType.epic: 1,
    WorkItemType.feature: 2,
    WorkItemType.story: 3,
    WorkItemType.task: 4,
    WorkItemType.bug: 4,
    WorkItemType.subtask: 5,
}


class WorkItemStatus(StrEnum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    blocked = "blocked"
    done = "done"
    cancelled = "cancelled"


CLOSED_STATUSES = {WorkItemStatus.done, WorkItemStatus.cancelled}


class Priority(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class LinkType(StrEnum):
    blocks = "blocks"
    relates_to = "relates_to"
    duplicates = "duplicates"


class MilestoneStatus(StrEnum):
    open = "open"
    completed = "completed"
    cancelled = "cancelled"


class SprintStatus(StrEnum):
    planned = "planned"
    active = "active"
    closed = "closed"


class RaidType(StrEnum):
    risk = "risk"
    assumption = "assumption"
    issue = "issue"
    dependency = "dependency"


class RaidStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    monitoring = "monitoring"
    resolved = "resolved"
    closed = "closed"
    accepted = "accepted"


OPEN_RAID_STATUSES = {RaidStatus.open, RaidStatus.in_progress, RaidStatus.monitoring}


class DecisionStatus(StrEnum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"
    superseded = "superseded"


class ActorType(StrEnum):
    user = "user"
    agent = "agent"
    system = "system"
