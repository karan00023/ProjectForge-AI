"""Domain rules for projects, work items, dependencies, milestones, sprints, RAID and decisions."""

import threading

from sqlalchemy import select

from app.models import AuditEvent
from tests.conftest import Api, World, make_item, make_project


def test_project_key_unique_and_validated(world: World) -> None:
    make_project(world.owner, "DUP")
    assert world.owner.post("/api/projects", json={"key": "DUP", "name": "x"}).status_code == 409
    assert world.owner.post("/api/projects", json={"key": "dup", "name": "x"}).status_code == 409
    for bad in ["1AB", "A", "TOOLONGKEY", "A-B"]:
        assert world.owner.post("/api/projects", json={"key": bad, "name": "x"}).status_code == 422
    # The same key is allowed in another organization.
    make_project(world.outsider, "DUP")


def test_project_from_template_creates_epics_and_baselined_milestones(world: World) -> None:
    p = make_project(world.owner, "MIG", template="data-migration", start_date="2026-06-01")
    assert p["kind"] == "data_platform" and p["methodology"] == "hybrid"
    epics = world.owner.get(f"/api/projects/{p['id']}/work-items", params={"type": "epic"}).json()
    assert [e["key"] for e in epics][:2] == ["MIG-1", "MIG-2"]
    assert len(epics) == 6
    ms = world.owner.get(f"/api/projects/{p['id']}/milestones").json()
    assert ms[0]["name"] == "Environments ready"
    assert ms[0]["baseline_date"] == ms[0]["planned_date"] == "2026-06-22"
    assert (
        world.owner.post(
            "/api/projects", json={"key": "BAD", "name": "x", "template": "nope"}
        ).status_code
        == 422
    )


def test_work_item_numbering_and_hierarchy_rules(world: World) -> None:
    p = make_project(world.owner)
    epic = make_item(world.owner, p["id"], type="epic", title="Epic")
    story = make_item(world.owner, p["id"], type="story", title="Story", parent_id=epic["id"])
    assert (epic["key"], story["key"]) == ("ALP-1", "ALP-2")
    # A story cannot contain an epic.
    r = world.owner.post(
        f"/api/projects/{p['id']}/work-items",
        json={"type": "epic", "title": "Bad", "parent_id": story["id"]},
    )
    assert r.status_code == 422
    # Changing the story into an initiative would put it above its own parent.
    r = world.owner.patch(f"/api/work-items/{story['id']}", json={"type": "initiative"})
    assert r.status_code == 422
    # Changing the epic into a subtask would put it below its child.
    r = world.owner.patch(f"/api/work-items/{epic['id']}", json={"type": "subtask"})
    assert r.status_code == 422
    detail = world.owner.get(f"/api/work-items/{epic['id']}").json()
    assert [c["key"] for c in detail["children"]] == ["ALP-2"]


def test_dates_and_null_rules(world: World) -> None:
    p = make_project(world.owner)
    r = world.owner.post(
        f"/api/projects/{p['id']}/work-items",
        json={"type": "task", "title": "x", "start_date": "2026-06-10", "due_date": "2026-06-01"},
    )
    assert r.status_code == 422
    item = make_item(world.owner, p["id"])
    assert (
        world.owner.patch(f"/api/work-items/{item['id']}", json={"title": None}).status_code == 422
    )
    assert world.owner.patch(f"/api/work-items/{item['id']}", json={"bogus": 1}).status_code == 422


def test_status_done_records_completion_and_audit(world: World, db) -> None:  # type: ignore[no-untyped-def]
    p = make_project(world.owner)
    item = make_item(world.owner, p["id"], title="Ship it")
    done = world.member.patch(f"/api/work-items/{item['id']}", json={"status": "done"}).json()
    assert done["completed_at"] is not None
    reopened = world.member.patch(
        f"/api/work-items/{item['id']}", json={"status": "in_progress"}
    ).json()
    assert reopened["completed_at"] is None
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "work_item")
        .order_by(AuditEvent.created_at)
    ).all()
    assert [e.summary for e in events] == [
        "Created story ALP-1: Ship it",
        "Moved ALP-1 from backlog to done",
        "Moved ALP-1 from done to in_progress",
    ]
    assert events[1].actor_label == "Mia Member"
    assert events[1].changes == {"status": {"from": "backlog", "to": "done"}}
    history = world.owner.get(f"/api/work-items/{item['id']}").json()["history"]
    assert len(history) == 3


def test_no_op_update_writes_no_audit(world: World, db) -> None:  # type: ignore[no-untyped-def]
    p = make_project(world.owner)
    item = make_item(world.owner, p["id"], title="Same")
    world.owner.patch(f"/api/work-items/{item['id']}", json={"title": "Same"})
    count = len(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "work_item")).all())
    assert count == 1


def test_dependency_cycles_are_rejected_with_path(world: World) -> None:
    p = make_project(world.owner)
    a, b, c = (make_item(world.owner, p["id"], title=t) for t in "abc")
    for src, dst in [(a, b), (b, c)]:
        assert (
            world.owner.post(
                f"/api/work-items/{src['id']}/links", json={"target_id": dst["id"]}
            ).status_code
            == 201
        )
    r = world.owner.post(f"/api/work-items/{c['id']}/links", json={"target_id": a["id"]})
    assert r.status_code == 409
    assert "ALP-3 → ALP-1 → ALP-2 → ALP-3" in r.json()["detail"]
    # Self-link and duplicate.
    assert (
        world.owner.post(
            f"/api/work-items/{a['id']}/links", json={"target_id": a["id"]}
        ).status_code
        == 422
    )
    assert (
        world.owner.post(
            f"/api/work-items/{a['id']}/links", json={"target_id": b["id"]}
        ).status_code
        == 409
    )
    # relates_to links do not participate in cycle checks.
    assert (
        world.owner.post(
            f"/api/work-items/{c['id']}/links", json={"target_id": a["id"], "type": "relates_to"}
        ).status_code
        == 201
    )
    links = world.owner.get(f"/api/work-items/{b['id']}").json()["links"]
    assert {(lk["direction"], lk["item"]["key"]) for lk in links} == {
        ("incoming", "ALP-1"),
        ("outgoing", "ALP-3"),
    }


def test_cross_project_dependencies_within_org(world: World) -> None:
    p1, p2 = make_project(world.owner, "ONE"), make_project(world.owner, "TWO")
    a, b = make_item(world.owner, p1["id"]), make_item(world.owner, p2["id"])
    assert (
        world.owner.post(
            f"/api/work-items/{a['id']}/links", json={"target_id": b["id"]}
        ).status_code
        == 201
    )
    assert len(world.owner.get(f"/api/projects/{p2['id']}/links").json()) == 1


def test_delete_item_reparents_children(world: World) -> None:
    p = make_project(world.owner)
    epic = make_item(world.owner, p["id"], type="epic", title="E")
    feature = make_item(world.owner, p["id"], type="feature", title="F", parent_id=epic["id"])
    story = make_item(world.owner, p["id"], type="story", title="S", parent_id=feature["id"])
    assert world.owner.delete(f"/api/work-items/{feature['id']}").status_code == 204
    assert world.owner.get(f"/api/work-items/{story['id']}").json()["parent_id"] == epic["id"]
    keys = [w["key"] for w in world.owner.get(f"/api/projects/{p['id']}/work-items").json()]
    assert keys == ["ALP-1", "ALP-3"]


def test_concurrent_creates_get_unique_numbers(world: World) -> None:
    p = make_project(world.owner)
    results: list[int] = []
    errors: list[str] = []

    def worker() -> None:
        api = Api("member@example.com")
        for _ in range(5):
            r = api.post(f"/api/projects/{p['id']}/work-items", json={"type": "task", "title": "t"})
            if r.status_code == 201:
                results.append(r.json()["number"])
            else:
                errors.append(r.text)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(results) == list(range(1, 21))


def test_milestone_variance_rebaseline_and_completion(world: World, db) -> None:  # type: ignore[no-untyped-def]
    p = make_project(world.owner)
    m = world.owner.post(
        f"/api/projects/{p['id']}/milestones", json={"name": "Beta", "planned_date": "2026-06-19"}
    ).json()
    assert m["variance_working_days"] == 0 and m["overdue"] is False
    m = world.owner.patch(f"/api/milestones/{m['id']}", json={"planned_date": "2026-06-26"}).json()
    assert m["baseline_date"] == "2026-06-19" and m["variance_working_days"] == 5
    r = world.owner.post(
        f"/api/milestones/{m['id']}/rebaseline", json={"reason": "Scope added by CR-12"}
    )
    assert r.json()["baseline_date"] == "2026-06-26" and r.json()["variance_working_days"] == 0
    assert (
        world.owner.post(
            f"/api/milestones/{m['id']}/rebaseline", json={"reason": "again"}
        ).status_code
        == 422
    )
    rebaseline = db.scalar(select(AuditEvent).where(AuditEvent.action == "rebaseline"))
    assert "Scope added by CR-12" in rebaseline.summary
    done = world.owner.patch(f"/api/milestones/{m['id']}", json={"status": "completed"}).json()
    assert done["actual_date"] == "2026-06-15"  # injected 'today'
    item = make_item(world.owner, p["id"], milestone_id=m["id"], status="done")
    make_item(world.owner, p["id"], milestone_id=m["id"])
    ms = world.owner.get(f"/api/projects/{p['id']}/milestones").json()[0]
    assert (ms["deliverables_done"], ms["deliverables_total"]) == (1, 2)
    assert item["completed_at"] is not None


def test_sprint_commitment_totals(world: World) -> None:
    p = make_project(world.owner)
    sp = world.owner.post(
        f"/api/projects/{p['id']}/sprints",
        json={
            "name": "S1",
            "start_date": "2026-06-15",
            "end_date": "2026-06-28",
            "capacity_points": 20,
        },
    ).json()
    make_item(world.owner, p["id"], sprint_id=sp["id"], story_points=5, status="done")
    make_item(world.owner, p["id"], sprint_id=sp["id"], story_points=8)
    make_item(world.owner, p["id"], sprint_id=sp["id"], story_points=13, status="cancelled")
    s = world.owner.get(f"/api/projects/{p['id']}/sprints").json()[0]
    assert (s["committed_points"], s["done_points"], s["capacity_points"]) == (13, 5, 20)
    bad = world.owner.post(
        f"/api/projects/{p['id']}/sprints",
        json={"name": "S2", "start_date": "2026-06-28", "end_date": "2026-06-15"},
    )
    assert bad.status_code == 422


def test_raid_rules_and_generated_score(world: World) -> None:
    p = make_project(world.owner)
    url = f"/api/projects/{p['id']}/raid"
    assert (
        world.owner.post(url, json={"type": "risk", "title": "No P", "impact": 4}).status_code
        == 422
    )
    assert (
        world.owner.post(
            url, json={"type": "issue", "title": "x", "impact": 4, "probability": 2}
        ).status_code
        == 422
    )
    assert (
        world.owner.post(
            url, json={"type": "risk", "title": "x", "impact": 6, "probability": 2}
        ).status_code
        == 422
    )
    item = make_item(world.owner, p["id"])
    risk = world.owner.post(
        url,
        json={
            "type": "risk",
            "title": "Vendor slips",
            "probability": 4,
            "impact": 5,
            "work_item_ids": [item["id"]],
        },
    ).json()
    assert (risk["key"], risk["score"], risk["work_item_ids"]) == ("ALP-R1", 20, [item["id"]])
    updated = world.owner.patch(
        f"/api/raid/{risk['id']}", json={"probability": 2, "work_item_ids": []}
    ).json()
    assert (updated["score"], updated["work_item_ids"]) == (10, [])
    issue = world.owner.post(url, json={"type": "issue", "title": "Env down", "impact": 3}).json()
    assert issue["score"] is None and issue["key"] == "ALP-R2"
    ordered = [r["key"] for r in world.owner.get(url).json()]
    assert ordered == ["ALP-R1", "ALP-R2"]
    assert [r["key"] for r in world.owner.get(url, params={"type": "issue"}).json()] == ["ALP-R2"]


def test_decisions_record_who_and_when_and_supersede(world: World) -> None:
    p = make_project(world.owner)
    url = f"/api/projects/{p['id']}/decisions"
    first = world.owner.post(
        url, json={"title": "Batch", "decision": "Nightly batch", "status": "accepted"}
    ).json()
    assert first["decided_by_id"] == str(world.users["owner"].id) and first["decided_at"]
    second = world.member.post(
        url,
        json={
            "title": "CDC",
            "decision": "Use CDC",
            "status": "accepted",
            "supersedes_id": first["id"],
            "alternatives": [{"option": "Batch", "cons": "Misses deletes"}],
        },
    ).json()
    assert second["key"] == "ALP-D2" and second["alternatives"][0]["option"] == "Batch"
    decisions = {d["key"]: d for d in world.owner.get(url).json()}
    assert decisions["ALP-D1"]["status"] == "superseded"
    proposed = world.owner.post(url, json={"title": "Tolerance", "decision": "0.01%"}).json()
    assert proposed["decided_at"] is None
    accepted = world.admin.patch(
        f"/api/decisions/{proposed['id']}", json={"status": "accepted"}
    ).json()
    assert accepted["decided_by_id"] == str(world.users["admin"].id)
