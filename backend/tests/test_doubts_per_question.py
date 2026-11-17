"""Doubts raised in chat during Q1, Q2 and Q3 must each end up as insights attached to
the question that was open when they were asked — whether the AI batch covers one
question (interval flush) or several (one flush at poll end)."""

import time

import pytest

from api.enums import BatchTrigger
from api.db.session import SessionLocal
from api.services.batch_dispatch_service import dispatch_batches
from api.workers import tasks

QUESTIONS = [
    {"prompt": "Which organelle makes most of a cell's ATP?",
     "options": [{"label": "Nucleus"}, {"label": "Mitochondrion", "is_correct": True}]},
    {"prompt": "What does a ribosome build?",
     "options": [{"label": "Proteins", "is_correct": True}, {"label": "Lipids"}]},
    {"prompt": "Where does photosynthesis happen?",
     "options": [{"label": "Chloroplast", "is_correct": True}, {"label": "Vacuole"}]},
]

# One distinctive doubt per question; the stub analyzer turns a "?" message into a
# STUDENT_QUESTION whose topic is built from the message's leading keywords.
DOUBTS = [
    "Mitochondria powerhouse why?",
    "Ribosomes build proteins how?",
    "Chloroplast sunlight needed?",
]
KEYWORD = ["mitochondria", "ribosomes", "chloroplast"]


def _ws(actor, room_id):
    return actor.use().websocket_connect(f"/api/ws/rooms/{room_id}")


def _drain_until(ws, kind):
    while True:
        event = ws.receive_json()
        if event["type"] == kind:
            return event


def _wait_pending(live, poll_id, expected, timeout=5.0):
    """Chat is buffered on a background thread after broadcast; wait for it to land."""
    deadline = time.monotonic() + timeout
    while live.pending_count(poll_id) < expected:
        assert time.monotonic() < deadline, f"only {live.pending_count(poll_id)} of {expected} messages buffered"
        time.sleep(0.02)


@pytest.fixture
def three_question_poll(classroom):
    teacher = classroom["teacher"]
    res = teacher.use().post(
        f"/api/rooms/{classroom['room_id']}/polls",
        json={"title": "Cell biology", "time_limit_seconds": 300, "questions": QUESTIONS},
    )
    assert res.status_code == 201, res.text
    poll = res.json()
    assert teacher.use().post(f"/api/polls/{poll['id']}/start").status_code == 200
    return poll


def _run_class(classroom, live, poll, flush_each_question: bool):
    """Two students ask a doubt during each question; the teacher advances, then ends."""
    teacher = classroom["teacher"]
    s1, s2 = classroom["students"]
    room_id, poll_id = classroom["room_id"], poll["id"]
    sent = 0
    with _ws(teacher, room_id) as wt, _ws(s1, room_id) as w1, _ws(s2, room_id) as w2:
        for i, doubt in enumerate(DOUBTS):
            for ws in (w1, w2):
                ws.send_json({"type": "chat", "content": doubt})
                _drain_until(wt, "chat")
                sent += 1
            _wait_pending(live, poll_id, 2 if flush_each_question else sent)
            if flush_each_question:
                with SessionLocal() as db:
                    dispatch_batches(db, live, poll_id, BatchTrigger.INTERVAL)
            if i < len(DOUBTS) - 1:
                assert teacher.use().post(f"/api/polls/{poll_id}/next-question").status_code == 200
    assert teacher.use().post(f"/api/polls/{poll_id}/end").status_code == 200
    tasks.persist_poll_results(poll_id)  # final flush of anything still buffered


def _analyze_all(published):
    for batch_id in list(published.analyze):
        tasks.analyze_batch.run(batch_id)


def _insights(classroom, poll_id, question_id=None):
    params = {"question_id": question_id} if question_id else {}
    res = classroom["teacher"].use().get(f"/api/polls/{poll_id}/insights", params=params)
    assert res.status_code == 200, res.text
    return res.json()["insights"]


def _assert_each_question_has_only_its_doubts(classroom, poll):
    poll_id = poll["id"]
    student_ids = {s.user["id"] for s in classroom["students"]}
    for i, question in enumerate(poll["questions"]):
        rows = _insights(classroom, poll_id, question["id"])
        text = " ".join((r["topic_label"] + " " + r["summary"]).lower() for r in rows)
        assert KEYWORD[i] in text, f"Q{i + 1} is missing its doubt: {rows}"
        for j, other in enumerate(KEYWORD):
            if j != i:
                assert other not in text, f"Q{i + 1} picked up Q{j + 1}'s doubt: {rows}"
        assert all(r["question_id"] == question["id"] for r in rows)
        asked = [r for r in rows if r["category"] == "STUDENT_QUESTION"]
        assert {r["student_id"] for r in asked} == student_ids, "each student's doubt should be credited to them"
        common = [r for r in rows if r["category"] == "COMMON_DOUBT"]
        assert len(common) == 1 and common[0]["support_count"] >= 2, "two students, same doubt → one common doubt"

    whole = _insights(classroom, poll_id)
    for word in KEYWORD:
        assert word in " ".join(r["topic_label"].lower() for r in whole), f"whole-poll view is missing {word!r}"


def test_doubts_on_each_question_flushed_per_question(classroom, live, published, three_question_poll):
    _run_class(classroom, live, three_question_poll, flush_each_question=True)
    assert len(published.analyze) == 3  # one batch per question
    _analyze_all(published)
    _assert_each_question_has_only_its_doubts(classroom, three_question_poll)


def test_doubts_on_each_question_flushed_together_at_poll_end(classroom, live, published, three_question_poll):
    _run_class(classroom, live, three_question_poll, flush_each_question=False)
    assert len(published.analyze) == 1  # one batch spanning Q1–Q3
    _analyze_all(published)
    _assert_each_question_has_only_its_doubts(classroom, three_question_poll)


# ---------- live LLM (opt-in: RUN_LIVE_LLM=1, uses the real key in .env) ----------
LIVE_DOUBTS = [
    ["Why is the mitochondria called the powerhouse? I thought the nucleus makes energy",
     "I'm confused, does the nucleus make ATP or the mitochondria?"],
    ["Do ribosomes make proteins or lipids? I always mix that up",
     "wait what do ribosomes actually build, I'm lost"],
    ["Does photosynthesis need sunlight to happen in the chloroplast?",
     "how does the chloroplast turn light into sugar? confused"],
]
LIVE_STEMS = [("mitochond", "nucleus", "atp"), ("ribosom", "protein"), ("chloroplast", "photosynth", "sunlight", "light")]


@pytest.mark.skipif(not __import__("os").environ.get("RUN_LIVE_LLM"), reason="set RUN_LIVE_LLM=1 to call the real LLM")
def test_live_llm_attaches_doubts_to_the_right_question(classroom, live, published, three_question_poll, monkeypatch):
    from dotenv import dotenv_values

    from api.config.settings import Settings
    from api.workers import llm_client

    real = Settings(_env_file=__import__("os").path.join(__import__("os").path.dirname(__file__), "..", ".env"),
                    LLM_PROVIDER=dotenv_values().get("LLM_PROVIDER") or "auto")
    assert real.llm_provider != "stub", "no LLM key in .env"
    monkeypatch.setattr(llm_client, "settings", real)

    teacher, (s1, s2) = classroom["teacher"], classroom["students"]
    room_id, poll = classroom["room_id"], three_question_poll
    sent = 0
    with _ws(teacher, room_id) as wt, _ws(s1, room_id) as w1, _ws(s2, room_id) as w2:
        for i, pair in enumerate(LIVE_DOUBTS):
            for ws, msg in zip((w1, w2), pair):
                ws.send_json({"type": "chat", "content": msg})
                _drain_until(wt, "chat")
                sent += 1
            _wait_pending(live, poll["id"], sent)
            if i < 2:
                teacher.use().post(f"/api/polls/{poll['id']}/next-question")
    teacher.use().post(f"/api/polls/{poll['id']}/end")
    tasks.persist_poll_results(poll["id"])
    _analyze_all(published)

    print(f"\nprovider={real.llm_provider} model={real.llm_model}")
    for i, question in enumerate(poll["questions"]):
        rows = _insights(classroom, poll["id"], question["id"])
        print(f"\nQ{i + 1}: {question['prompt']}")
        for r in rows:
            print(f"  [{r['category']}] {r['topic_label']} — {r['summary']} (student: {r['student_name']})")
        text = " ".join((r["topic_label"] + " " + r["summary"]).lower() for r in rows)
        assert rows and any(s in text for s in LIVE_STEMS[i]), f"Q{i + 1} doubts not reflected"
        others = [s for j, stems in enumerate(LIVE_STEMS) if j != i for s in stems[:1]]
        assert not any(s in text for s in others), f"Q{i + 1} picked up another question's doubt"
    general = [r for r in _insights(classroom, poll["id"]) if r["question_id"] is None]
    print("\nWhole-poll only:", [f"[{r['category']}] {r['topic_label']}" for r in general])
