from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.config import get_settings
from app.main import app
from app.models import UserSession
from tests.conftest import PASSWORD, Api, World


def test_login_sets_httponly_cookie_and_me_works(world: World) -> None:
    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": "OWNER@example.com", "password": PASSWORD})
    assert r.status_code == 204
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "owner@example.com"
    assert me["role"] == "owner"
    assert me["organization"]["name"] == "Acme"


def test_wrong_password_and_unknown_email_get_same_401(world: World) -> None:
    client = TestClient(app)
    bad_pw = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "x"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()


def test_session_token_is_stored_hashed(world: World, db) -> None:  # type: ignore[no-untyped-def]
    raw = world.owner.client.cookies.get(get_settings().session_cookie_name)
    hashes = db.scalars(select(UserSession.token_hash)).all()
    assert raw not in hashes
    assert all(len(h) == 64 for h in hashes)


def test_logout_revokes_session_server_side(world: World) -> None:
    api = world.owner
    token = api.client.cookies.get(get_settings().session_cookie_name)
    assert api.post("/api/auth/logout").status_code == 204
    replay = TestClient(app, cookies={get_settings().session_cookie_name: token})
    assert replay.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected(world: World, db) -> None:  # type: ignore[no-untyped-def]
    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()
    assert world.owner.get("/api/auth/me").status_code == 401


def test_unauthenticated_requests_are_rejected() -> None:
    client = TestClient(app)
    for url in ["/api/projects", "/api/dashboard", "/api/search?q=x", "/api/auth/me"]:
        assert client.get(url).status_code == 401, url


def test_login_is_rate_limited(world: World) -> None:
    client = TestClient(app)
    limit = get_settings().login_rate_limit_attempts
    for _ in range(limit):
        client.post("/api/auth/login", json={"email": "owner@example.com", "password": "nope"})
    r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_mutations_require_csrf_header(world: World) -> None:
    api = world.owner
    del api.client.headers["X-Requested-With"]
    r = api.post("/api/projects", json={"key": "NOC", "name": "No CSRF"})
    assert r.status_code == 403
    assert "X-Requested-With" in r.json()["detail"]


def test_security_headers_present(world: World) -> None:
    r = world.owner.get("/api/projects")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Request-Id"]


def test_demo_login_only_for_demo_users_and_only_in_demo_mode(world: World, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = TestClient(app)
    client.headers["X-Requested-With"] = "test"
    # Regular (non-demo) accounts cannot be impersonated through demo login.
    r = client.post("/api/auth/demo-login", json={"email": "owner@example.com"})
    assert r.status_code == 404
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert client.get("/api/auth/demo-personas").json() == []
    assert client.post("/api/auth/demo-login", json={"email": "x@example.com"}).status_code == 404


def test_org_switching_requires_membership(world: World) -> None:
    other = Api("owner@example.com", org_id=str(world.org_b.id))
    assert other.get("/api/auth/me").status_code == 404
    garbage = Api("owner@example.com", org_id="not-a-uuid")
    assert garbage.get("/api/projects").status_code == 404
