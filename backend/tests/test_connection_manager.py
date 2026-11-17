import asyncio

import pytest

from api.enums import UserRole
from api.realtime.connection_manager import Connection, ConnectionManager


class FakeSocket:
    def __init__(self, *, fail: bool = False, delay: float = 0.0):
        self.sent: list[dict] = []
        self.fail = fail
        self.delay = delay
        self.closed = False

    async def send_json(self, data):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("socket is dead")
        self.sent.append(data)

    async def close(self, code: int = 1000):
        self.closed = True


def conn(sock, role=UserRole.STUDENT, user_id="u"):
    return Connection(websocket=sock, user_id=user_id, role=role, full_name=user_id)


def run(coro):
    return asyncio.run(coro)


def test_broadcast_reaches_every_socket_in_room_only():
    async def scenario():
        m = ConnectionManager()
        a, b, other = FakeSocket(), FakeSocket(), FakeSocket()
        await m.register("r1", conn(a, user_id="a"))
        await m.register("r1", conn(b, user_id="b"))
        await m.register("r2", conn(other, user_id="o"))
        await m.broadcast("r1", {"type": "chat"})
        return a, b, other

    a, b, other = run(scenario())
    assert a.sent == [{"type": "chat"}] and b.sent == [{"type": "chat"}]
    assert other.sent == []


def test_unregister_stops_delivery():
    async def scenario():
        m = ConnectionManager()
        a = FakeSocket()
        c = conn(a)
        await m.register("r1", c)
        await m.unregister("r1", c.id)
        await m.broadcast("r1", {"type": "chat"})
        return a, m

    a, m = run(scenario())
    assert a.sent == [] and m.snapshot("r1") == []


@pytest.mark.parametrize("bad", [FakeSocket(fail=True), FakeSocket(delay=1.0)])
def test_dead_or_slow_socket_is_pruned_and_others_still_receive(bad):
    async def scenario():
        m = ConnectionManager(send_timeout=0.2)
        good = FakeSocket()
        await m.register("r1", conn(good, user_id="good"))
        await m.register("r1", conn(bad, user_id="bad"))
        await m.broadcast("r1", {"type": "chat", "n": 1})
        await m.broadcast("r1", {"type": "chat", "n": 2})
        return good, m

    good, m = run(scenario())
    assert [e["n"] for e in good.sent] == [1, 2]
    assert [c.user_id for c in m.snapshot("r1")] == ["good"]
    assert bad.closed


def test_role_filtered_broadcast():
    async def scenario():
        m = ConnectionManager()
        t, s = FakeSocket(), FakeSocket()
        await m.register("r1", conn(t, role=UserRole.TEACHER, user_id="t"))
        await m.register("r1", conn(s, user_id="s"))
        await m.broadcast("r1", {"type": "insights_updated"}, role=UserRole.TEACHER)
        return t, s

    t, s = run(scenario())
    assert t.sent and not s.sent
