"""Test setup: PostgreSQL tables live in an isolated `test_suite` schema inside the
configured database (dropped afterwards); Redis is fakeredis with Lua; Celery
publishing and worker→API callbacks are captured instead of sent."""

import os
import uuid

from dotenv import dotenv_values

_env = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
_base_url = os.environ.get("TEST_DATABASE_URL") or _env.get("DATABASE_URL")
TEST_SCHEMA = "test_suite"
os.environ["DATABASE_URL"] = f"{_base_url}{'&' if '?' in _base_url else '?'}options=-csearch_path%3D{TEST_SCHEMA}"
os.environ["AUTH_RATE_LIMIT"] = "1000/minute"
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-0123456789")
os.environ.setdefault("INTERNAL_SHARED_SECRET", "test-internal-secret")
os.environ["LLM_PROVIDER"] = "stub"
# The TestClient speaks plain http://testserver, which never sends Secure cookies; the
# dev .env enables them for the ngrok deployment, so force them off here.
os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from api.db.session import engine  # noqa: E402
from api.main import create_app  # noqa: E402
from api.models import Base  # noqa: E402
from api.realtime.live_state import LiveStateStore  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {TEST_SCHEMA}"))
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))


@pytest.fixture(autouse=True)
def clean_tables(database):
    yield
    names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} CASCADE"))


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


@pytest.fixture
def live(redis_client):
    return LiveStateStore(redis_client)


class Published:
    def __init__(self):
        self.analyze: list[str] = []
        self.persist: list[str] = []
        self.auto_end: list[str] = []
        self.revoked: list[str] = []
        self.internal: list[tuple[str, dict]] = []


@pytest.fixture
def published(monkeypatch, live):
    from api.workers import dispatch, tasks

    record = Published()
    monkeypatch.setattr(dispatch, "publish_analyze", record.analyze.append)
    monkeypatch.setattr(dispatch, "publish_persist", record.persist.append)
    monkeypatch.setattr(dispatch, "schedule_auto_end", lambda pid, eta: record.auto_end.append(pid))
    monkeypatch.setattr(dispatch, "revoke", record.revoked.extend)
    monkeypatch.setattr(tasks, "live_state", lambda: live)

    def fake_post(path, payload=None):
        record.internal.append((path, payload or {}))

        class _Resp:
            def raise_for_status(self):
                return None

        return _Resp()

    monkeypatch.setattr(tasks, "_internal_post", fake_post)
    return record


@pytest.fixture
def client(redis_client, published):
    app = create_app(redis_client=redis_client)
    with TestClient(app) as c:
        yield c


class Actor:
    """A logged-in user; `use()` switches the shared client's cookie jar to them."""

    def __init__(self, client: TestClient, body: dict, cookies: list):
        self.client = client
        self.body = body
        self.cookies = cookies
        self.user = body["user"]
        self.room = body.get("room")

    def use(self) -> TestClient:
        self.client.cookies.clear()
        for cookie in self.cookies:
            self.client.cookies.jar.set_cookie(cookie)
        return self.client


@pytest.fixture
def make_user(client):
    def _make(role: str, name: str | None = None) -> Actor:
        client.cookies.clear()
        name = name or f"{role.title()} {uuid.uuid4().hex[:6]}"
        res = client.post(
            "/api/auth/register",
            json={"email": f"{uuid.uuid4().hex[:10]}@example.com", "password": "password123", "full_name": name, "role": role},
        )
        assert res.status_code == 201, res.text
        return Actor(client, res.json(), list(client.cookies.jar))

    return _make


SAMPLE_QUESTIONS = [
    {"prompt": "2 + 2 = ?", "options": [{"label": "3"}, {"label": "4", "is_correct": True}, {"label": "5"}]},
    {"prompt": "Capital of France?", "options": [{"label": "Paris", "is_correct": True}, {"label": "Rome"}]},
]


@pytest.fixture
def classroom(make_user):
    """A teacher with a draft poll and two students who joined the room."""
    teacher = make_user("TEACHER", "Ada Teacher")
    s1 = make_user("STUDENT", "Sam One")
    s2 = make_user("STUDENT", "Kim Two")
    room_id = teacher.room["id"]
    for s in (s1, s2):
        assert s.use().post(f"/api/rooms/{room_id}/join").status_code == 200
    res = teacher.use().post(
        f"/api/rooms/{room_id}/polls", json={"title": "Warm-up", "time_limit_seconds": 120, "questions": SAMPLE_QUESTIONS}
    )
    assert res.status_code == 201, res.text
    return {"teacher": teacher, "students": [s1, s2], "room_id": room_id, "poll": res.json()}
