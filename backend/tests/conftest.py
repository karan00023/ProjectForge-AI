"""Test harness: a real PostgreSQL database, migrated with Alembic, truncated between tests."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://projectforge:projectforge@localhost:5432/projectforge_test",
    ),
)
os.environ["ENVIRONMENT"] = "test"
os.environ["DEMO_MODE"] = "true"

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from app.api.auth import login_limiter
from app.core.deps import get_today
from app.core.security import hash_password
from app.db import get_engine, get_sessionmaker
from app.main import app
from app.models import Base, Membership, Organization, User
from app.models.enums import Role

TODAY = date(2026, 6, 15)  # a Monday
PASSWORD = "correct horse battery staple"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> Iterator[None]:
    engine = get_engine()
    # The harness wipes the schema; never let it touch a development or production database.
    if not (engine.url.database or "").endswith("_test"):
        pytest.exit(
            f"Refusing to run tests against '{engine.url.database}': name must end in _test"
        )
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    login_limiter.reset()
    app.dependency_overrides[get_today] = lambda: TODAY
    yield
    app.dependency_overrides.clear()
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


class Api:
    """TestClient bound to one signed-in user. Sends the CSRF header like the real frontend."""

    def __init__(self, email: str | None = None, org_id: str | None = None) -> None:
        self.client = TestClient(app)
        self.client.headers["X-Requested-With"] = "test"
        if org_id:
            self.client.headers["X-Org-Id"] = org_id
        if email:
            r = self.client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
            assert r.status_code == 204, r.text

    def get(self, url: str, **kw):  # type: ignore[no-untyped-def]
        return self.client.get(url, **kw)

    def post(self, url: str, json=None, **kw):  # type: ignore[no-untyped-def]
        return self.client.post(url, json=json, **kw)

    def patch(self, url: str, json=None, **kw):  # type: ignore[no-untyped-def]
        return self.client.patch(url, json=json, **kw)

    def delete(self, url: str, **kw):  # type: ignore[no-untyped-def]
        return self.client.delete(url, **kw)


@dataclass
class World:
    org_a: Organization
    org_b: Organization
    owner: Api
    admin: Api
    member: Api
    viewer: Api
    outsider: Api  # owner of org B
    users: dict[str, User]


def _user(db: Session, key: str, name: str) -> User:
    u = User(email=f"{key}@example.com", name=name, password_hash=hash_password(PASSWORD))
    db.add(u)
    return u


@pytest.fixture
def world(db: Session) -> World:
    org_a = Organization(name="Acme", slug="acme")
    org_b = Organization(name="Globex", slug="globex")
    db.add_all([org_a, org_b])
    users = {
        "owner": _user(db, "owner", "Olivia Owner"),
        "admin": _user(db, "admin", "Adam Admin"),
        "member": _user(db, "member", "Mia Member"),
        "viewer": _user(db, "viewer", "Victor Viewer"),
        "outsider": _user(db, "outsider", "Oscar Outsider"),
    }
    db.flush()
    for key, role in [
        ("owner", Role.owner),
        ("admin", Role.admin),
        ("member", Role.member),
        ("viewer", Role.viewer),
    ]:
        db.add(Membership(organization_id=org_a.id, user_id=users[key].id, role=role))
    db.add(Membership(organization_id=org_b.id, user_id=users["outsider"].id, role=Role.owner))
    db.commit()
    return World(
        org_a=org_a,
        org_b=org_b,
        owner=Api("owner@example.com"),
        admin=Api("admin@example.com"),
        member=Api("member@example.com"),
        viewer=Api("viewer@example.com"),
        outsider=Api("outsider@example.com"),
        users=users,
    )


def make_project(api: Api, key: str = "ALP", **extra) -> dict:  # type: ignore[no-untyped-def]
    r = api.post("/api/projects", json={"key": key, "name": f"Project {key}", **extra})
    assert r.status_code == 201, r.text
    return r.json()


def make_item(api: Api, project_id: str, **fields) -> dict:  # type: ignore[no-untyped-def]
    body = {"type": "story", "title": "Item"} | fields
    r = api.post(f"/api/projects/{project_id}/work-items", json=body)
    assert r.status_code == 201, r.text
    return r.json()
