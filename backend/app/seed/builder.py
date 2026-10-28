"""Small builder used by the demo seed. Dates are offsets from 'today' so the demo stays current."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Decision,
    Membership,
    Milestone,
    Organization,
    Project,
    RaidItem,
    Sprint,
    Team,
    TeamMember,
    User,
    WorkItem,
    WorkItemLink,
)
from app.models.enums import (
    ActorType,
    DecisionStatus,
    LinkType,
    MilestoneStatus,
    Priority,
    RaidStatus,
    RaidType,
    Role,
    SprintStatus,
    WorkItemStatus,
    WorkItemType,
)

DEMO_PASSWORD = "projectforge-demo"


@dataclass
class Ctx:
    org: Organization
    project: Project


class Seeder:
    def __init__(self, db: Session, today: date) -> None:
        self.db = db
        self.today = today
        self.users: dict[str, User] = {}
        self._password_hash = hash_password(DEMO_PASSWORD)

    # ---- time helpers -------------------------------------------------------------------

    def d(self, offset: int | None) -> date | None:
        return None if offset is None else self.today + timedelta(days=offset)

    def ts(self, offset_days: float, hour: int = 10) -> datetime:
        base = datetime.combine(self.today, time(hour, 0), tzinfo=UTC)
        return base + timedelta(days=offset_days)

    # ---- identity -----------------------------------------------------------------------

    def org(self, name: str, slug: str) -> Organization:
        org = Organization(id=uuid.uuid4(), name=name, slug=slug, is_demo=True)
        self.db.add(org)
        return org

    def user(self, key: str, name: str, title: str, color: str) -> User:
        email = f"{key}@demo.projectforge.dev"
        u = User(
            id=uuid.uuid4(),
            email=email,
            name=name,
            title=title,
            avatar_color=color,
            is_demo=True,
            password_hash=self._password_hash,
        )
        self.db.add(u)
        self.users[key] = u
        return u

    def member(self, org: Organization, key: str, role: Role) -> None:
        self.db.add(Membership(organization_id=org.id, user_id=self.users[key].id, role=role))

    def team(
        self, org: Organization, name: str, members: list[tuple[str, str, int, list[str]]]
    ) -> Team:
        t = Team(id=uuid.uuid4(), organization_id=org.id, name=name)
        self.db.add(t)
        for key, role_title, hours, skills in members:
            t.members.append(
                TeamMember(
                    user_id=self.users[key].id,
                    role_title=role_title,
                    weekly_capacity_hours=hours,
                    skills=skills,
                )
            )
        return t

    # ---- project data -------------------------------------------------------------------

    def project(self, org: Organization, team: Team | None, owner: str, **fields: Any) -> Ctx:
        start = fields.pop("start")
        target = fields.pop("target")
        p = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            team_id=team.id if team else None,
            owner_id=self.users[owner].id,
            start_date=self.d(start),
            target_date=self.d(target),
            created_at=self.ts(start - 7),
            wip_limits=fields.pop("wip_limits", {}),
            **fields,
        )
        self.db.add(p)
        self.db.flush()
        ctx = Ctx(org, p)
        self.event(
            ctx, "project", p.id, owner, "create", f"Created project {p.key} — {p.name}", start - 7
        )
        return ctx

    def sprint(
        self,
        c: Ctx,
        name: str,
        start: int,
        end: int,
        status: SprintStatus,
        capacity: int,
        goal: str,
    ) -> Sprint:
        s = Sprint(
            id=uuid.uuid4(),
            organization_id=c.org.id,
            project_id=c.project.id,
            name=name,
            goal=goal,
            start_date=self.d(start),
            end_date=self.d(end),
            status=status,
            capacity_points=capacity,
        )
        self.db.add(s)
        return s

    def milestone(
        self,
        c: Ctx,
        name: str,
        baseline: int,
        planned: int,
        owner: str,
        actual: int | None = None,
        description: str | None = None,
    ) -> Milestone:
        m = Milestone(
            id=uuid.uuid4(),
            organization_id=c.org.id,
            project_id=c.project.id,
            name=name,
            description=description,
            baseline_date=self.d(baseline),
            planned_date=self.d(planned),
            actual_date=self.d(actual),
            status=MilestoneStatus.completed if actual is not None else MilestoneStatus.open,
            owner_id=self.users[owner].id,
        )
        self.db.add(m)
        self.db.flush()
        if planned != baseline and actual is None:
            self.event(
                c,
                "milestone",
                m.id,
                owner,
                "update",
                f"Moved milestone '{name}' forecast to {self.d(planned)}",
                min(-1, planned - 30),
                {"planned_date": {"from": str(self.d(baseline)), "to": str(self.d(planned))}},
            )
        if actual is not None:
            self.event(
                c, "milestone", m.id, owner, "update", f"Completed milestone '{name}'", actual
            )
        return m

    def item(
        self,
        c: Ctx,
        type_: WorkItemType,
        title: str,
        *,
        parent: WorkItem | None = None,
        status: WorkItemStatus = WorkItemStatus.backlog,
        points: int | None = None,
        assignee: str | None = None,
        reporter: str | None = None,
        priority: Priority = Priority.medium,
        start: int | None = None,
        due: int | None = None,
        done_on: int | None = None,
        created: int | None = None,
        sprint: Sprint | None = None,
        milestone: Milestone | None = None,
        description: str | None = None,
        ac: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> WorkItem:
        p = c.project
        number = p.next_item_number
        p.next_item_number += 1
        created_offset = (
            created if created is not None else ((p.start_date or self.today) - self.today).days
        )
        reporter = reporter or self._owner_key(p)
        w = WorkItem(
            id=uuid.uuid4(),
            organization_id=c.org.id,
            project_id=p.id,
            parent_id=parent.id if parent else None,
            number=number,
            type=type_,
            title=title,
            description=description,
            status=status,
            priority=priority,
            story_points=points,
            start_date=self.d(start),
            due_date=self.d(due),
            completed_at=self.ts(done_on, 16) if done_on is not None else None,
            assignee_id=self.users[assignee].id if assignee else None,
            reporter_id=self.users[reporter].id,
            sprint_id=sprint.id if sprint else None,
            milestone_id=milestone.id if milestone else None,
            acceptance_criteria=[
                {
                    "id": uuid.uuid4().hex[:8],
                    "text": t,
                    "format": "gherkin" if t.lower().startswith("given") else "plain",
                }
                for t in (ac or [])
            ],
            labels=labels or [],
            rank=float(number),
            created_at=self.ts(created_offset, 9),
            updated_at=self.ts(done_on if done_on is not None else max(created_offset, -3), 15),
        )
        self.db.add(w)
        label = f"{p.key}-{number}"
        self.event(
            c,
            "work_item",
            w.id,
            reporter,
            "create",
            f"Created {type_.value} {label}: {title}",
            created_offset,
        )
        if done_on is not None and status == WorkItemStatus.done:
            self.event(
                c,
                "work_item",
                w.id,
                assignee or reporter,
                "update",
                f"Moved {label} from in_review to done",
                done_on,
                {"status": {"from": "in_review", "to": "done"}},
            )
        return w

    def link(self, c: Ctx, source: WorkItem, target: WorkItem, lag: int = 0) -> None:
        self.db.flush()  # links have no ORM relationship, so items must be inserted first
        self.db.add(
            WorkItemLink(
                organization_id=c.org.id,
                source_id=source.id,
                target_id=target.id,
                type=LinkType.blocks,
                lag_days=lag,
                created_at=self.ts(-60),
            )
        )

    def raid(
        self,
        c: Ctx,
        type_: RaidType,
        title: str,
        *,
        owner: str,
        impact: int,
        probability: int | None = None,
        priority: Priority = Priority.medium,
        status: RaidStatus = RaidStatus.open,
        description: str | None = None,
        mitigation: str | None = None,
        contingency: str | None = None,
        trigger: str | None = None,
        evidence: str | None = None,
        due: int | None = None,
        milestone: Milestone | None = None,
        items: list[WorkItem] | None = None,
        created: int = -30,
    ) -> RaidItem:
        p = c.project
        number = p.next_raid_number
        p.next_raid_number += 1
        r = RaidItem(
            id=uuid.uuid4(),
            organization_id=c.org.id,
            project_id=p.id,
            number=number,
            type=type_,
            title=title,
            description=description,
            status=status,
            priority=priority,
            probability=probability,
            impact=impact,
            mitigation=mitigation,
            contingency=contingency,
            escalation_trigger=trigger,
            evidence=evidence,
            owner_id=self.users[owner].id,
            due_date=self.d(due),
            milestone_id=milestone.id if milestone else None,
            created_at=self.ts(created),
        )
        r.work_items = items or []
        self.db.add(r)
        self.event(
            c,
            "raid_item",
            r.id,
            owner,
            "create",
            f"Logged {type_.value} {p.key}-R{number}: {title}",
            created,
        )
        return r

    def decision(
        self,
        c: Ctx,
        title: str,
        *,
        decision: str,
        by: str,
        on: int,
        status: DecisionStatus = DecisionStatus.accepted,
        context: str | None = None,
        rationale: str | None = None,
        alternatives: list[dict[str, str]] | None = None,
        impact: str | None = None,
    ) -> Decision:
        p = c.project
        number = p.next_decision_number
        p.next_decision_number += 1
        decided = status in {DecisionStatus.accepted, DecisionStatus.rejected}
        d = Decision(
            id=uuid.uuid4(),
            organization_id=c.org.id,
            project_id=p.id,
            number=number,
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            alternatives=alternatives or [],
            impact=impact,
            status=status,
            decided_by_id=self.users[by].id if decided else None,
            decided_at=self.ts(on, 14) if decided else None,
            created_at=self.ts(on - 2),
        )
        self.db.add(d)
        self.event(
            c,
            "decision",
            d.id,
            by,
            "create",
            f"Recorded decision {p.key}-D{number} ({status.value}): {title}",
            on,
        )
        return d

    def event(
        self,
        c: Ctx,
        entity_type: str,
        entity_id: uuid.UUID,
        actor: str,
        action: str,
        summary: str,
        offset_days: float,
        changes: dict[str, Any] | None = None,
    ) -> None:
        u = self.users[actor]
        at = self.ts(offset_days, 11)
        self.db.add(
            AuditEvent(
                organization_id=c.org.id,
                created_at=at,
                actor_type=ActorType.user,
                actor_user_id=u.id,
                actor_label=u.name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                project_id=c.project.id,
                summary=summary,
                changes=changes or {},
            )
        )
        if c.project.last_activity_at is None or at > c.project.last_activity_at:
            c.project.last_activity_at = at

    def _owner_key(self, p: Project) -> str:
        return next(k for k, u in self.users.items() if u.id == p.owner_id)
