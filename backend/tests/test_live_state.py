import uuid

from api.realtime import redis_keys as K
from api.realtime.live_state import now_ms

POLL, ROOM = "poll-1", "room-1"


def setup_poll(live, *, deadline_offset_ms=60_000, questions=2):
    qids = [str(uuid.uuid4()) for _ in range(questions)]
    options = {q: [str(uuid.uuid4()), str(uuid.uuid4())] for q in qids}
    live.init_poll(
        poll_id=POLL, room_id=ROOM, deadline_ms=now_ms() + deadline_offset_ms,
        question_map={q: {"options": o, "correct": o[0]} for q, o in options.items()},
        first_question_id=qids[0], participant_ids=["early-bird"],
    )
    return qids, options


def chat(i, student="s1", q=None):
    return {"msg_id": str(i), "student_id": student, "question_id": q, "received_ms": now_ms(), "content": f"m{i}"}


def test_first_valid_answer_wins(live):
    qids, opts = setup_poll(live)
    q = qids[0]
    first = live.accept_answer(POLL, q, "s1", opts[q][0])
    second = live.accept_answer(POLL, q, "s1", opts[q][1])
    assert first.outcome == "accepted" and first.seq == 1 and first.answered_count == 1
    assert second.outcome == "duplicate" and second.option_id == opts[q][0]
    assert live.accept_answer(POLL, q, "s2", opts[q][1]).seq == 2


def test_answer_rejections(live):
    qids, opts = setup_poll(live)
    assert live.accept_answer(POLL, qids[1], "s1", opts[qids[1]][0]).outcome == "not_current"
    assert live.accept_answer(POLL, qids[0], "s1", "nope").outcome == "invalid_option"
    setup_poll(live, deadline_offset_ms=-1)
    q = live.get_meta(POLL)["current_question_id"]
    assert live.accept_answer(POLL, q, "s1", "x").outcome == "expired"


def test_open_question_moves_current_and_detects_races(live):
    qids, opts = setup_poll(live)
    assert live.open_question(POLL, qids[0], qids[1], 1) == "ok"
    assert live.open_question(POLL, qids[0], qids[1], 1) == "stale"
    assert live.accept_answer(POLL, qids[1], "s1", opts[qids[1]][0]).outcome == "accepted"


def test_close_snapshot_stops_answers_and_chat(live):
    qids, opts = setup_poll(live)
    live.accept_answer(POLL, qids[0], "s1", opts[qids[0]][0])
    snap = live.close_and_snapshot(POLL, ROOM)
    assert snap.previous_status == "ACTIVE"
    assert [(a.student_id, a.seq) for a in snap.answers] == [("s1", 1)]
    assert snap.participant_ids == {"early-bird", "s1"}
    assert live.get_active_poll_id(ROOM) is None
    assert live.accept_answer(POLL, qids[0], "s2", opts[qids[0]][0]).outcome == "closed"
    assert live.buffer_chat(POLL, chat(1)) == -1
    # A retried close still returns the same snapshot.
    assert len(live.close_and_snapshot(POLL, ROOM).answers) == 1


def test_claim_batch_takes_at_most_fifty_and_respects_minimum(live):
    setup_poll(live)
    for i in range(120):
        live.buffer_chat(POLL, chat(i))
    assert live.claim_batch(POLL, min_count=200) is None
    b1 = live.claim_batch(POLL, min_count=50)
    b2 = live.claim_batch(POLL, min_count=50)
    assert len(b1[1]) == 50 and len(b2[1]) == 50
    assert live.claim_batch(POLL, min_count=50) is None  # 20 left < threshold
    assert [m["msg_id"] for m in b1[1]][:2] == ["0", "1"]
    assert live.inflight_count(POLL) == 2
    b3 = live.claim_batch(POLL, min_count=1)
    assert len(b3[1]) == 20
    assert live.redis.zscore(K.FLUSH_INDEX, POLL) is None
    live.ack_batch(POLL, b1[0])
    assert live.inflight_count(POLL) == 2 and live.get_batch(POLL, b1[0]) == []


def test_cancel_cleanup_removes_all_poll_keys_but_meta(live):
    qids, opts = setup_poll(live)
    live.accept_answer(POLL, qids[0], "s1", opts[qids[0]][0])
    for i in range(3):
        live.buffer_chat(POLL, chat(i))
    batch_id, _ = live.claim_batch(POLL, 1)
    live.buffer_chat(POLL, chat(99))
    live.cancel_cleanup(POLL, ROOM)
    leftover = {k.decode() for k in live.redis.scan_iter(match=f"poll:{POLL}:*")}
    assert leftover == {K.meta(POLL)}
    assert live.get_meta(POLL)["status"] == "CANCELLED"
    assert live.get_active_poll_id(ROOM) is None
    assert live.redis.zscore(K.FLUSH_INDEX, POLL) is None
    assert live.buffer_chat(POLL, chat(100)) == -1
