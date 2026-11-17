from sqlalchemy import func, select

from api.db.session import SessionLocal
from api.models import PollParticipant, Room, StudentAnswer
from api.realtime import redis_keys as K
from api.workers import tasks


def test_teacher_registration_provisions_exactly_one_room(client, make_user):
    teacher = make_user("TEACHER", "Grace")
    assert teacher.room and teacher.room["name"] == "Grace's Room"
    client.cookies.clear()
    res = client.post("/api/auth/login", json={"email": teacher.user["email"], "password": "password123"})
    assert res.status_code == 200 and res.json()["room"]["id"] == teacher.room["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Room)) == 1


def test_auth_cookies_refresh_and_logout(client, make_user):
    student = make_user("STUDENT")
    assert student.room is None
    c = student.use()
    assert c.get("/api/auth/me").json()["user"]["role"] == "STUDENT"
    assert c.post("/api/auth/refresh").status_code == 200
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_students_cannot_call_teacher_apis_and_teachers_only_own_room(classroom, make_user):
    s1 = classroom["students"][0]
    poll_id = classroom["poll"]["id"]
    assert s1.use().post(f"/api/polls/{poll_id}/start").json()["error_code"] == "INVALID_ROLE"
    other = make_user("TEACHER")
    assert other.use().post(f"/api/polls/{poll_id}/start").status_code == 404
    assert other.client.get(f"/api/rooms/{classroom['room_id']}/participants").status_code == 403


def test_start_validation_reports_problems(classroom):
    t = classroom["teacher"].use()
    res = t.post(f"/api/rooms/{classroom['room_id']}/polls", json={"title": "Empty"})
    bad = t.post(f"/api/polls/{res.json()['id']}/start")
    assert bad.status_code == 422 and bad.json()["error_code"] == "POLL_INVALID_FOR_START"


def test_full_poll_lifecycle(classroom, live, published):
    teacher, (s1, s2) = classroom["teacher"], classroom["students"]
    poll = classroom["poll"]
    poll_id, q1, q2 = poll["id"], poll["questions"][0], poll["questions"][1]
    correct_q1 = next(o["id"] for o in q1["options"] if o["is_correct"])
    wrong_q1 = next(o["id"] for o in q1["options"] if not o["is_correct"])

    c = teacher.use()
    with c.websocket_connect(f"/api/ws/rooms/{classroom['room_id']}") as ws_teacher:
        assert ws_teacher.receive_json()["type"] == "presence"
        started = c.post(f"/api/polls/{poll_id}/start")
        assert started.status_code == 200, started.text
        assert started.json()["current_question"]["id"] == q1["id"]
        assert ws_teacher.receive_json()["type"] == "poll_started"
        opened = ws_teacher.receive_json()
        assert opened["type"] == "question_opened"
        assert all("is_correct" not in o for o in opened["question"]["options"])  # never leaked
        assert published.auto_end == [poll_id]
        assert c.post(f"/api/polls/{poll_id}/start").json()["error_code"] == "POLL_NOT_DRAFT"

        # Students answer: first valid answer wins; s2 is first correct.
        r = s2.use().post(f"/api/polls/{poll_id}/answers", json={"question_id": q1["id"], "option_id": correct_q1})
        assert r.json()["status"] == "accepted"
        r = s1.use().post(f"/api/polls/{poll_id}/answers", json={"question_id": q1["id"], "option_id": wrong_q1})
        assert r.json()["status"] == "accepted"
        again = s1.client.post(f"/api/polls/{poll_id}/answers", json={"question_id": q1["id"], "option_id": correct_q1})
        assert again.json()["status"] == "duplicate" and again.json()["option_id"] == wrong_q1
        not_current = s1.client.post(
            f"/api/polls/{poll_id}/answers", json={"question_id": q2["id"], "option_id": q2["options"][0]["id"]}
        )
        assert not_current.json()["error_code"] == "ANSWER_NOT_CURRENT"
        live_s1 = s1.client.get(f"/api/rooms/{classroom['room_id']}/active-poll").json()
        assert live_s1["my_answer_option_id"] == wrong_q1 and live_s1["answered_count"] is None

        assert c.__class__  # keep linter calm
        teacher.use()
        progress = [ws_teacher.receive_json() for _ in range(2)]
        assert [p["answered_count"] for p in progress] == [1, 2]
        assert progress[0]["option_id"] == correct_q1
        live_t = c.get(f"/api/polls/{poll_id}/live").json()
        assert live_t["option_counts"] == {correct_q1: 1, wrong_q1: 1}

        nxt = c.post(f"/api/polls/{poll_id}/next-question")
        assert nxt.json()["current_question"]["id"] == q2["id"] and nxt.json()["answered_count"] == 0
        assert ws_teacher.receive_json()["type"] == "question_opened"
        assert c.post(f"/api/polls/{poll_id}/next-question").json()["error_code"] == "NO_MORE_QUESTIONS"

        ended = c.post(f"/api/polls/{poll_id}/end")
        assert ended.status_code == 200, ended.text
        res = ended.json()
        assert res["questions"][0]["first_correct_student"]["full_name"] == "Kim Two"
        assert res["questions"][0]["answered_count"] == 2 and res["participant_count"] == 2
        assert res["questions"][1]["answered_count"] == 0
        event = ws_teacher.receive_json()
        assert event["type"] == "poll_ended" and event["results"]["poll_id"] == poll_id

    # Late answers are refused; repeated end returns the same results.
    late = s1.use().post(f"/api/polls/{poll_id}/answers", json={"question_id": q2["id"], "option_id": q2["options"][0]["id"]})
    assert late.json()["error_code"] == "ANSWER_POLL_CLOSED"
    assert teacher.use().post(f"/api/polls/{poll_id}/end").json() == res

    # Before persistence, students already see results and their review (from Redis).
    assert published.persist == [poll_id]
    review = s1.use().get(f"/api/me/polls/{poll_id}/review").json()
    assert review["answered_count"] == 1 and review["correct_count"] == 0
    assert [i["poll_id"] for i in s1.client.get("/api/me/polls").json()["items"]] == [poll_id]

    # Async persistence moves everything to PostgreSQL and clears Redis.
    tasks.persist_poll_results(poll_id)
    tasks.persist_poll_results(poll_id)  # idempotent
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StudentAnswer)) == 2
        assert db.scalar(select(func.count()).select_from(PollParticipant)) == 2
    assert live.get_results(poll_id) is None
    assert s1.client.get(f"/api/polls/{poll_id}/results").json()["questions"] == res["questions"]
    review = s1.client.get(f"/api/me/polls/{poll_id}/review").json()
    q_review = review["questions"][0]
    assert q_review["selected_option_id"] == wrong_q1 and q_review["is_correct"] is False
    assert review["questions"][1]["selected_option_id"] is None
    detail = teacher.use().get(f"/api/polls/{poll_id}").json()
    assert detail["results_status"] == "PERSISTED" and detail["analysis_status"] == "COMPLETE"


def test_cancel_clears_redis_and_poll_subtree(classroom, live, published):
    teacher, s1 = classroom["teacher"], classroom["students"][0]
    poll = classroom["poll"]
    q1 = poll["questions"][0]
    c = teacher.use()
    assert c.post(f"/api/polls/{poll['id']}/start").status_code == 200
    s1.use().post(f"/api/polls/{poll['id']}/answers", json={"question_id": q1["id"], "option_id": q1["options"][0]["id"]})

    res = teacher.use().post(f"/api/polls/{poll['id']}/cancel")
    assert res.status_code == 200 and res.json()["status"] == "CANCELLED"
    assert teacher.client.post(f"/api/polls/{poll['id']}/cancel").status_code == 200  # idempotent
    leftovers = {k.decode() for k in live.redis.scan_iter(match=f"poll:{poll['id']}:*")}
    assert leftovers == {K.meta(poll["id"])}
    assert teacher.client.get(f"/api/polls/{poll['id']}").json()["questions"] == []
    assert teacher.client.get(f"/api/polls/{poll['id']}/results").json()["error_code"] == "RESULTS_NOT_AVAILABLE"
    assert s1.use().get("/api/me/polls").json()["items"] == []


def test_auto_end_endpoint_is_noop_before_deadline(classroom, client):
    from api.config.settings import settings

    poll_id = classroom["poll"]["id"]
    assert classroom["teacher"].use().post(f"/api/polls/{poll_id}/start").status_code == 200
    res = client.post(f"/api/internal/polls/{poll_id}/auto-end", headers={"X-Internal-Secret": settings.INTERNAL_SHARED_SECRET})
    assert res.json()["message"] == "not due"
    bad = client.post(f"/api/internal/polls/{poll_id}/auto-end", headers={"X-Internal-Secret": "wrong"})
    assert bad.status_code == 403
