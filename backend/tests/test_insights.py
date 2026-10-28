"""Explainable health, command-center aggregates, activity, search, and the demo seed."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.models import Project, User
from app.seed.demo import seed_demo
from tests.conftest import TODAY, Api, World, make_item, make_project


def health(api: Api, project_id: str) -> dict:
    return api.get(f"/api/projects/{project_id}/health").json()


def codes(h: dict) -> dict[str, str]:
    return {s["code"]: s["level"] for s in h["signals"]}


def test_fresh_project_is_green_with_honest_progress(world: World) -> None:
    p = make_project(world.owner)
    make_item(world.owner, p["id"], type="epic", title="Container, not counted")
    make_item(world.owner, p["id"], story_points=3, status="done")
    make_item(world.owner, p["id"], story_points=5)
    make_item(world.owner, p["id"])  # unestimated
    h = health(world.owner, p["id"])
    assert h["level"] == "green" and h["signals"] == []
    assert h["progress"] == {
        "items_total": 3,
        "items_done": 1,
        "points_total": 8,
        "points_done": 3,
        "unestimated_items": 1,
    }
    assert h["evaluated_on"] == TODAY.isoformat() and h["rules_version"]


def test_overdue_milestone_is_red_with_evidence(world: World) -> None:
    p = make_project(world.owner)
    m = world.owner.post(
        f"/api/projects/{p['id']}/milestones",
        json={"name": "Go-live", "planned_date": "2026-06-12"},
    ).json()
    h = health(world.owner, p["id"])
    assert codes(h) == {"milestone_overdue": "red"}
    assert h["signals"][0]["evidence"] == [
        {"entity_type": "milestone", "id": m["id"], "label": "Go-live"}
    ]
    world.owner.patch(f"/api/milestones/{m['id']}", json={"status": "completed"})
    assert health(world.owner, p["id"])["level"] == "green"


def test_slip_against_baseline_thresholds(world: World) -> None:
    p = make_project(world.owner)
    m = world.owner.post(
        f"/api/projects/{p['id']}/milestones", json={"name": "Beta", "planned_date": "2026-07-01"}
    ).json()
    url = f"/api/milestones/{m['id']}"
    world.owner.patch(url, json={"planned_date": "2026-07-08"})  # +5 wd: tolerated
    assert health(world.owner, p["id"])["level"] == "green"
    world.owner.patch(url, json={"planned_date": "2026-07-09"})  # +6 wd
    assert codes(health(world.owner, p["id"])) == {"milestone_slipped": "amber"}
    world.owner.patch(url, json={"planned_date": "2026-07-16"})  # +11 wd
    assert codes(health(world.owner, p["id"])) == {"milestone_slipped": "red"}


def test_overdue_and_blocked_items(world: World) -> None:
    p = make_project(world.owner)
    late = make_item(world.owner, p["id"], due_date="2026-06-12")
    make_item(world.owner, p["id"], due_date="2026-06-12", status="done")  # done: not overdue
    make_item(world.owner, p["id"], due_date="2026-06-15")  # due today: not overdue
    h = health(world.owner, p["id"])
    assert codes(h) == {"items_overdue": "amber"}
    assert [e["label"] for e in h["signals"][0]["evidence"]] == [late["key"]]
    world.owner.patch(f"/api/work-items/{late['id']}", json={"priority": "critical"})
    assert codes(health(world.owner, p["id"])) == {"items_overdue": "red"}

    q = make_project(world.owner, "BLK")
    m = world.owner.post(
        f"/api/projects/{q['id']}/milestones", json={"name": "M", "planned_date": "2026-08-01"}
    ).json()
    b = make_item(world.owner, q["id"], status="blocked")
    assert codes(health(world.owner, q["id"])) == {"items_blocked": "amber"}
    world.owner.patch(f"/api/work-items/{b['id']}", json={"milestone_id": m["id"]})
    assert codes(health(world.owner, q["id"])) == {"items_blocked": "red"}


def test_risk_and_issue_signals(world: World) -> None:
    p = make_project(world.owner)
    url = f"/api/projects/{p['id']}/raid"
    world.owner.post(url, json={"type": "risk", "title": "Low", "probability": 2, "impact": 3})
    assert health(world.owner, p["id"])["level"] == "green"
    mid = world.owner.post(
        url, json={"type": "risk", "title": "Mid", "probability": 2, "impact": 5}
    ).json()
    assert codes(health(world.owner, p["id"])) == {"elevated_risk": "amber"}
    high = world.owner.post(
        url, json={"type": "risk", "title": "High", "probability": 4, "impact": 4}
    ).json()
    assert codes(health(world.owner, p["id"])) == {"elevated_risk": "amber", "high_risk": "red"}
    for r in (mid, high):
        world.owner.patch(f"/api/raid/{r['id']}", json={"status": "closed"})
    world.owner.post(
        url, json={"type": "issue", "title": "Outage", "impact": 5, "priority": "critical"}
    )
    assert codes(health(world.owner, p["id"])) == {"critical_issue": "red"}


def test_stale_and_inactive_projects(world: World, db) -> None:  # type: ignore[no-untyped-def]
    p = make_project(world.owner)
    db.execute(update(Project).values(last_activity_at=datetime.now(UTC) - timedelta(days=15)))
    db.commit()
    assert codes(health(world.owner, p["id"])) == {"stale_data": "amber"}
    world.owner.post(
        f"/api/projects/{p['id']}/milestones", json={"name": "Old", "planned_date": "2026-01-01"}
    )
    world.owner.patch(f"/api/projects/{p['id']}", json={"status": "completed"})
    # Closed projects are not evaluated against delivery rules.
    assert health(world.owner, p["id"])["level"] == "green"


def test_dashboard_kpis_lists_and_since_last_visit(world: World, db) -> None:  # type: ignore[no-untyped-def]
    p = make_project(world.owner)
    db.execute(
        update(User)
        .where(User.id == world.users["owner"].id)
        .values(previous_seen_at=datetime.now(UTC) - timedelta(hours=1))
    )
    db.commit()
    make_item(world.member, p["id"], title="Blocked thing", status="blocked")
    make_item(world.member, p["id"], title="Done thing", status="done")
    make_item(world.owner, p["id"], title="My own change")  # own changes are not "new to me"
    m = world.owner.post(
        f"/api/projects/{p['id']}/milestones", json={"name": "Soon", "planned_date": "2026-06-20"}
    ).json()
    world.owner.patch(
        f"/api/milestones/{m['id']}", json={"status": "completed", "actual_date": "2026-06-19"}
    )
    world.owner.post(
        f"/api/projects/{p['id']}/raid",
        json={"type": "risk", "title": "Big", "probability": 5, "impact": 4},
    )
    world.owner.post(
        f"/api/projects/{p['id']}/decisions", json={"title": "Pending", "decision": "TBD"}
    )

    d = world.owner.get("/api/dashboard").json()
    kpis = {k["id"]: k for k in d["kpis"]}
    assert kpis["active_projects"]["value"] == 1
    assert kpis["completed_14d"]["value"] == 1
    assert kpis["milestone_on_time"]["display"] == "100%"
    assert (kpis["milestone_on_time"]["numerator"], kpis["milestone_on_time"]["denominator"]) == (
        1,
        1,
    )
    assert kpis["critical_raid"]["value"] == 1
    assert [w["title"] for w in d["blocked_items"]] == ["Blocked thing"]
    assert [r["title"] for r in d["critical_risks"]] == ["Big"]
    assert [x["title"] for x in d["pending_decisions"]] == ["Pending"]
    assert d["changes_since_last_visit"] == 2
    assert d["recent_activity"][0]["summary"].startswith("Recorded decision")


def test_on_time_kpi_shows_dash_without_completed_milestones(world: World) -> None:
    make_project(world.owner)
    kpi = {k["id"]: k for k in world.owner.get("/api/dashboard").json()["kpis"]}[
        "milestone_on_time"
    ]
    assert kpi["value"] is None and kpi["display"] == "—"


def test_search_full_text_and_key_lookup(world: World) -> None:
    p = make_project(world.owner, "DPM", name="Data platform")
    make_item(world.owner, p["id"], title="Enable change data capture on orders")
    make_item(world.owner, p["id"], title="Unrelated", description="Nothing to see")
    world.owner.post(
        f"/api/projects/{p['id']}/raid",
        json={"type": "risk", "title": "Orders replication lag", "probability": 2, "impact": 2},
    )
    labels = [h["label"] for h in world.owner.get("/api/search", params={"q": "orders"}).json()]
    assert set(labels) == {"DPM-1", "DPM-R1"}
    exact = world.owner.get("/api/search", params={"q": "dpm-2"}).json()
    assert exact[0]["label"] == "DPM-2" and exact[0]["title"] == "Unrelated"
    assert world.owner.get("/api/search", params={"q": ""}).status_code == 422


def test_activity_feed_filters(world: World) -> None:
    p1, p2 = make_project(world.owner, "ONE"), make_project(world.owner, "TWO")
    make_item(world.owner, p1["id"], title="in one")
    make_item(world.owner, p2["id"], title="in two")
    feed = world.owner.get("/api/activity", params={"project_id": p1["id"]}).json()
    assert [e["summary"] for e in feed] == [
        "Created story ONE-1: in one",
        "Created project ONE — Project ONE",
    ]
    assert len(world.owner.get("/api/activity", params={"limit": 1}).json()) == 1


def test_demo_seed_loads_and_tells_a_coherent_story(db) -> None:  # type: ignore[no-untyped-def]
    seed_demo(db, TODAY)
    db.commit()
    personas = Api().get("/api/auth/demo-personas").json()
    assert personas[0]["name"] == "Priya Raman"  # sorted by organization, then role
    meridian = [p for p in personas if p["organization"] == "Meridian Freight Co."]
    assert meridian[0]["role"] == "owner" and meridian[-1]["role"] == "viewer"

    api = Api()
    api.client.headers["X-Requested-With"] = "test"
    assert (
        api.post("/api/auth/demo-login", json={"email": "priya@demo.projectforge.dev"}).status_code
        == 204
    )
    d = api.get("/api/dashboard").json()
    by_key = {p["key"]: p for p in d["projects"]}
    assert set(by_key) == {"DPM", "RAG", "TWS"}  # Orbital's project is not visible
    assert by_key["DPM"]["health"]["level"] == "red"
    dpm_codes = {s["code"] for s in by_key["DPM"]["health"]["signals"]}
    assert {"items_blocked", "high_risk", "milestone_slipped"} <= dpm_codes
    assert by_key["RAG"]["health"]["level"] == "red"
    assert by_key["TWS"]["health"]["level"] in {"green", "amber"}
    assert d["changes_since_last_visit"] > 0
    # Re-seeding is idempotent.
    seed_demo(db, TODAY)
    db.commit()
