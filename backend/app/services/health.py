"""Explainable project health.

Health is the worst of a set of explicit rules evaluated over stored records. Each rule that
fires produces a signal carrying the records that caused it, so every red or amber status in the
UI can be traced to evidence. Nothing here is estimated by a model.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Milestone, Project, RaidItem, WorkItem
from app.models.enums import (
    CLOSED_STATUSES,
    OPEN_RAID_STATUSES,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    RaidType,
    WorkItemStatus,
    WorkItemType,
)
from app.services.calendar import working_days_between

RULES_VERSION = "2026.10-1"

SLIP_AMBER_DAYS = 5
SLIP_RED_DAYS = 10
OVERDUE_ITEMS_RED_COUNT = 3
RISK_RED_SCORE = 15
RISK_AMBER_SCORE = 10
STALE_AFTER = timedelta(days=14)

# Units of delivery counted for progress. Containers (initiative/epic/feature) and subtasks are
# excluded so that work is not counted twice.
DELIVERY_TYPES = {WorkItemType.story, WorkItemType.task, WorkItemType.bug}

Level = Literal["green", "amber", "red"]
_ORDER = {"green": 0, "amber": 1, "red": 2}


@dataclass
class Evidence:
    entity_type: Literal["work_item", "milestone", "raid_item", "project"]
    id: uuid.UUID
    label: str


@dataclass
class Signal:
    code: str
    level: Literal["amber", "red"]
    message: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Progress:
    items_total: int = 0
    items_done: int = 0
    points_total: int = 0
    points_done: int = 0
    unestimated_items: int = 0


@dataclass
class Health:
    project_id: uuid.UUID
    level: Level
    signals: list[Signal]
    progress: Progress
    evaluated_on: date
    rules_version: str = RULES_VERSION


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _worst(signals: list[Signal]) -> Level:
    level: Level = "green"
    for s in signals:
        if _ORDER[s.level] > _ORDER[level]:
            level = s.level
    return level


def evaluate(
    db: Session,
    org_id: uuid.UUID,
    projects: list[Project],
    today: date,
    now: datetime | None = None,
) -> dict[uuid.UUID, Health]:
    """Evaluate health for many projects with a constant number of queries."""
    now = now or datetime.now(UTC)
    ids = [p.id for p in projects]
    if not ids:
        return {}

    milestones = db.scalars(
        select(Milestone).where(
            Milestone.organization_id == org_id,
            Milestone.project_id.in_(ids),
            Milestone.deleted_at.is_(None),
            Milestone.status == MilestoneStatus.open,
        )
    ).all()
    items = db.scalars(
        select(WorkItem).where(
            WorkItem.organization_id == org_id,
            WorkItem.project_id.in_(ids),
            WorkItem.deleted_at.is_(None),
        )
    ).all()
    raid = db.scalars(
        select(RaidItem).where(
            RaidItem.organization_id == org_id,
            RaidItem.project_id.in_(ids),
            RaidItem.deleted_at.is_(None),
            RaidItem.status.in_(OPEN_RAID_STATUSES),
        )
    ).all()

    by_project_ms: dict[uuid.UUID, list[Milestone]] = defaultdict(list)
    for m in milestones:
        by_project_ms[m.project_id].append(m)
    by_project_items: dict[uuid.UUID, list[WorkItem]] = defaultdict(list)
    for w in items:
        by_project_items[w.project_id].append(w)
    by_project_raid: dict[uuid.UUID, list[RaidItem]] = defaultdict(list)
    for r in raid:
        by_project_raid[r.project_id].append(r)

    open_milestone_ids = {m.id for m in milestones}
    result: dict[uuid.UUID, Health] = {}
    for project in projects:
        key = project.key
        progress = _progress(by_project_items[project.id])
        signals: list[Signal] = []
        if project.status in {ProjectStatus.active, ProjectStatus.on_hold, ProjectStatus.proposed}:
            signals += _milestone_signals(by_project_ms[project.id], today)
            signals += _item_signals(key, by_project_items[project.id], today, open_milestone_ids)
            signals += _raid_signals(key, by_project_raid[project.id])
            if project.status == ProjectStatus.active:
                last = project.last_activity_at
                if last is None or now - last > STALE_AFTER:
                    signals.append(
                        Signal(
                            "stale_data",
                            "amber",
                            "No recorded activity in the last 14 days — status may be out of date.",
                            [Evidence("project", project.id, key)],
                        )
                    )
        result[project.id] = Health(project.id, _worst(signals), signals, progress, today)
    return result


def _progress(items: list[WorkItem]) -> Progress:
    p = Progress()
    for w in items:
        if w.type not in DELIVERY_TYPES or w.status == WorkItemStatus.cancelled:
            continue
        p.items_total += 1
        done = w.status == WorkItemStatus.done
        p.items_done += int(done)
        if w.story_points is None:
            p.unestimated_items += 1
        else:
            p.points_total += w.story_points
            p.points_done += w.story_points if done else 0
    return p


def _milestone_signals(milestones: list[Milestone], today: date) -> list[Signal]:
    overdue = [m for m in milestones if m.planned_date < today]
    signals: list[Signal] = []
    if overdue:
        signals.append(
            Signal(
                "milestone_overdue",
                "red",
                f"{_plural(len(overdue), 'milestone')} past planned date and not completed: "
                + ", ".join(f"{m.name} (due {m.planned_date.isoformat()})" for m in overdue),
                [Evidence("milestone", m.id, m.name) for m in overdue],
            )
        )
    overdue_ids = {m.id for m in overdue}
    slipped = [
        (m, working_days_between(m.baseline_date, m.planned_date))
        for m in milestones
        if m.id not in overdue_ids
    ]
    red = [(m, d) for m, d in slipped if d > SLIP_RED_DAYS]
    amber = [(m, d) for m, d in slipped if SLIP_AMBER_DAYS < d <= SLIP_RED_DAYS]
    for level, group in (("red", red), ("amber", amber)):
        if group:
            signals.append(
                Signal(
                    "milestone_slipped",
                    level,  # type: ignore[arg-type]
                    "Forecast later than baseline: "
                    + ", ".join(f"{m.name} +{d} working days" for m, d in group),
                    [Evidence("milestone", m.id, m.name) for m, _ in group],
                )
            )
    return signals


def _item_signals(
    key: str, items: list[WorkItem], today: date, open_milestone_ids: set[uuid.UUID]
) -> list[Signal]:
    signals: list[Signal] = []
    live = [w for w in items if w.status not in CLOSED_STATUSES]
    overdue = sorted(
        (w for w in live if w.due_date is not None and w.due_date < today),
        key=lambda w: w.due_date or today,
    )
    if overdue:
        critical = any(w.priority == Priority.critical for w in overdue)
        level: Literal["amber", "red"] = (
            "red" if len(overdue) >= OVERDUE_ITEMS_RED_COUNT or critical else "amber"
        )
        signals.append(
            Signal(
                "items_overdue",
                level,
                f"{_plural(len(overdue), 'work item')} past due date"
                + (" (including critical priority)" if critical else ""),
                [Evidence("work_item", w.id, f"{key}-{w.number}") for w in overdue],
            )
        )
    blocked = [w for w in live if w.status == WorkItemStatus.blocked]
    if blocked:
        on_milestone = [w for w in blocked if w.milestone_id in open_milestone_ids]
        signals.append(
            Signal(
                "items_blocked",
                "red" if on_milestone else "amber",
                f"{_plural(len(blocked), 'work item')} blocked"
                + (f", {len(on_milestone)} of them milestone deliverables" if on_milestone else ""),
                [Evidence("work_item", w.id, f"{key}-{w.number}") for w in blocked],
            )
        )
    return signals


def _raid_signals(key: str, raid: list[RaidItem]) -> list[Signal]:
    signals: list[Signal] = []
    risks = [r for r in raid if r.type == RaidType.risk and r.probability is not None]
    scores = {r.id: r.probability * r.impact for r in risks if r.probability is not None}
    red = [r for r in risks if scores[r.id] >= RISK_RED_SCORE]
    amber = [r for r in risks if RISK_AMBER_SCORE <= scores[r.id] < RISK_RED_SCORE]
    if red:
        signals.append(
            Signal(
                "high_risk",
                "red",
                f"{_plural(len(red), 'open risk')} scored ≥ {RISK_RED_SCORE} "
                "(probability × impact)",
                [Evidence("raid_item", r.id, f"{key}-R{r.number}") for r in red],
            )
        )
    if amber:
        signals.append(
            Signal(
                "elevated_risk",
                "amber",
                f"{_plural(len(amber), 'open risk')} scored "
                f"{RISK_AMBER_SCORE}–{RISK_RED_SCORE - 1}",
                [Evidence("raid_item", r.id, f"{key}-R{r.number}") for r in amber],
            )
        )
    issues = [r for r in raid if r.type == RaidType.issue]
    crit = [r for r in issues if r.priority == Priority.critical]
    high = [r for r in issues if r.priority == Priority.high]
    if crit:
        signals.append(
            Signal(
                "critical_issue",
                "red",
                f"{_plural(len(crit), 'critical issue')} open",
                [Evidence("raid_item", r.id, f"{key}-R{r.number}") for r in crit],
            )
        )
    if high:
        signals.append(
            Signal(
                "high_issue",
                "amber",
                f"{_plural(len(high), 'high-priority issue')} open",
                [Evidence("raid_item", r.id, f"{key}-R{r.number}") for r in high],
            )
        )
    return signals
