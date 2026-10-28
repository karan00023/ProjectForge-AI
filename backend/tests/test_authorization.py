"""Role-based access control and tenant isolation.

Isolation is tested for every resource type: a user of another organization must get 404
(not 403) for reads and writes, so the existence of foreign records is never disclosed.
"""

import pytest

from tests.conftest import Api, World, make_item, make_project


@pytest.fixture
def fixture_ids(world: World) -> dict[str, str]:
    p = make_project(world.owner, "ACM")
    item = make_item(world.owner, p["id"], title="Secret roadmap item")
    other = make_item(world.owner, p["id"], title="Other")
    ms = world.owner.post(
        f"/api/projects/{p['id']}/milestones", json={"name": "M1", "planned_date": "2026-07-01"}
    ).json()
    sp = world.owner.post(
        f"/api/projects/{p['id']}/sprints",
        json={"name": "S1", "start_date": "2026-06-15", "end_date": "2026-06-28"},
    ).json()
    risk = world.owner.post(
        f"/api/projects/{p['id']}/raid",
        json={"type": "risk", "title": "Confidential risk", "probability": 3, "impact": 3},
    ).json()
    dec = world.owner.post(
        f"/api/projects/{p['id']}/decisions", json={"title": "Pick vendor", "decision": "Vendor X"}
    ).json()
    link = world.owner.post(
        f"/api/work-items/{item['id']}/links", json={"target_id": other["id"]}
    ).json()
    return {
        "project": p["id"],
        "item": item["id"],
        "other": other["id"],
        "milestone": ms["id"],
        "sprint": sp["id"],
        "risk": risk["id"],
        "decision": dec["id"],
        "link": link["id"],
    }


def mutations(ids: dict[str, str]) -> list[tuple[str, str, dict | None]]:
    p = ids["project"]
    return [
        ("post", "/api/projects", {"key": "NEW", "name": "New"}),
        ("patch", f"/api/projects/{p}", {"name": "Renamed"}),
        ("delete", f"/api/projects/{p}", None),
        ("post", f"/api/projects/{p}/work-items", {"type": "task", "title": "x"}),
        ("patch", f"/api/work-items/{ids['item']}", {"title": "changed"}),
        ("delete", f"/api/work-items/{ids['item']}", None),
        (
            "post",
            f"/api/work-items/{ids['other']}/links",
            {"target_id": ids["item"], "type": "relates_to"},
        ),
        ("delete", f"/api/work-item-links/{ids['link']}", None),
        ("post", f"/api/projects/{p}/milestones", {"name": "M", "planned_date": "2026-08-01"}),
        ("patch", f"/api/milestones/{ids['milestone']}", {"name": "M2"}),
        ("post", f"/api/milestones/{ids['milestone']}/rebaseline", {"reason": "because"}),
        ("delete", f"/api/milestones/{ids['milestone']}", None),
        (
            "post",
            f"/api/projects/{p}/sprints",
            {"name": "S", "start_date": "2026-07-01", "end_date": "2026-07-14"},
        ),
        ("patch", f"/api/sprints/{ids['sprint']}", {"name": "S2"}),
        ("post", f"/api/projects/{p}/raid", {"type": "issue", "title": "x", "impact": 2}),
        ("patch", f"/api/raid/{ids['risk']}", {"title": "changed"}),
        ("delete", f"/api/raid/{ids['risk']}", None),
        ("post", f"/api/projects/{p}/decisions", {"title": "t", "decision": "d"}),
        ("patch", f"/api/decisions/{ids['decision']}", {"title": "changed"}),
    ]


def reads(ids: dict[str, str]) -> list[str]:
    p = ids["project"]
    return [
        f"/api/projects/{p}",
        f"/api/projects/{p}/health",
        f"/api/projects/{p}/work-items",
        f"/api/projects/{p}/links",
        f"/api/projects/{p}/milestones",
        f"/api/projects/{p}/sprints",
        f"/api/projects/{p}/raid",
        f"/api/projects/{p}/decisions",
        f"/api/work-items/{ids['item']}",
        f"/api/raid/{ids['risk']}",
        f"/api/activity?project_id={p}",
    ]


def call(api: Api, method: str, url: str, body: dict | None):  # type: ignore[no-untyped-def]
    return getattr(api, method)(url, json=body) if body is not None else getattr(api, method)(url)


def test_viewer_can_read_but_never_write(world: World, fixture_ids: dict[str, str]) -> None:
    for url in reads(fixture_ids):
        assert world.viewer.get(url).status_code == 200, url
    for method, url, body in mutations(fixture_ids):
        r = call(world.viewer, method, url, body)
        assert r.status_code == 403, (method, url, r.status_code)


def test_member_can_write_but_not_delete_projects(
    world: World, fixture_ids: dict[str, str]
) -> None:
    assert (
        world.member.patch(
            f"/api/projects/{fixture_ids['project']}", json={"name": "M"}
        ).status_code
        == 200
    )
    assert world.member.delete(f"/api/projects/{fixture_ids['project']}").status_code == 403
    assert world.admin.delete(f"/api/projects/{fixture_ids['project']}").status_code == 204
    # Soft-deleted projects disappear from reads.
    assert world.owner.get(f"/api/projects/{fixture_ids['project']}").status_code == 404


def test_other_tenant_gets_404_on_every_read(world: World, fixture_ids: dict[str, str]) -> None:
    for url in reads(fixture_ids):
        assert world.outsider.get(url).status_code == 404, url


def test_other_tenant_gets_404_on_every_write(world: World, fixture_ids: dict[str, str]) -> None:
    for method, url, body in mutations(fixture_ids):
        if url == "/api/projects":
            continue  # creating a project in your own org is allowed
        r = call(world.outsider, method, url, body)
        assert r.status_code == 404, (method, url, r.status_code)
    # Nothing changed for the owning tenant.
    item = world.owner.get(f"/api/work-items/{fixture_ids['item']}").json()
    assert item["title"] == "Secret roadmap item"


def test_other_tenant_sees_nothing_in_lists_search_and_dashboard(
    world: World, fixture_ids: dict[str, str]
) -> None:
    assert world.outsider.get("/api/projects").json() == []
    assert world.outsider.get("/api/search", params={"q": "secret"}).json() == []
    assert world.outsider.get("/api/search", params={"q": "ACM-1"}).json() == []
    assert world.outsider.get("/api/activity").json() == []
    dash = world.outsider.get("/api/dashboard").json()
    assert dash["projects"] == [] and dash["critical_risks"] == []
    # And the owner does see their own record.
    hits = world.owner.get("/api/search", params={"q": "secret"}).json()
    assert [h["label"] for h in hits] == ["ACM-1"]


def test_cannot_reference_records_or_people_from_another_tenant(
    world: World, fixture_ids: dict[str, str]
) -> None:
    own = make_project(world.outsider, "GLX")
    own_item = make_item(world.outsider, own["id"])
    # Link to a foreign item.
    r = world.outsider.post(
        f"/api/work-items/{own_item['id']}/links", json={"target_id": fixture_ids["item"]}
    )
    assert r.status_code == 404
    # Parent / milestone / sprint from a foreign project.
    for field in ("parent_id", "milestone_id", "sprint_id"):
        source = {"parent_id": "item", "milestone_id": "milestone", "sprint_id": "sprint"}[field]
        r = world.outsider.post(
            f"/api/projects/{own['id']}/work-items",
            json={"type": "task", "title": "x", field: fixture_ids[source]},
        )
        assert r.status_code == 404, field
    # Assigning a user who is not a member of the organization.
    r = world.outsider.post(
        f"/api/projects/{own['id']}/work-items",
        json={"type": "task", "title": "x", "assignee_id": str(world.users["owner"].id)},
    )
    assert r.status_code == 422


def test_members_list_is_scoped(world: World) -> None:
    names = {m["user"]["name"] for m in world.owner.get("/api/org/members").json()}
    assert names == {"Olivia Owner", "Adam Admin", "Mia Member", "Victor Viewer"}
    assert [m["user"]["name"] for m in world.outsider.get("/api/org/members").json()] == [
        "Oscar Outsider"
    ]
