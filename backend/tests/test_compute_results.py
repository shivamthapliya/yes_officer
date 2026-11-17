import uuid
from datetime import UTC, datetime

from api.services.results_service import AnswerFact, compute_poll_results

T = datetime(2026, 1, 1, tzinfo=UTC)
Q1, A, B, S1, S2, S3, S4 = (str(uuid.uuid4()) for _ in range(7))
QUESTIONS = [
    {
        "id": Q1, "position": 0, "prompt": "?",
        "options": [
            {"id": A, "position": 0, "label": "A", "is_correct": False},
            {"id": B, "position": 1, "label": "B", "is_correct": True},
        ],
    }
]


def test_first_correct_student_is_decided_by_seq_not_timestamp():
    answers = [
        AnswerFact(Q1, S1, A, T, 1),
        AnswerFact(Q1, S3, B, T, 3),  # same timestamp as s2…
        AnswerFact(Q1, S2, B, T, 2),  # …but accepted first
    ]
    res = compute_poll_results(
        poll_id="00000000-0000-0000-0000-000000000001", title="t", ended_at=T, questions=QUESTIONS,
        answers=answers, participant_ids={S1, S4}, names={S2: "Second"},
    )
    q = res.questions[0]
    assert q.first_correct_student.full_name == "Second"
    assert (q.answered_count, q.correct_count, q.participant_count) == (3, 2, 4)
    assert [(o.label, o.count, o.percentage) for o in q.options] == [("A", 1, 33.3), ("B", 2, 66.7)]


def test_no_answers_gives_zeroes_and_no_first_student():
    res = compute_poll_results(
        poll_id="00000000-0000-0000-0000-000000000001", title="t", ended_at=T, questions=QUESTIONS,
        answers=[], participant_ids=set(), names={},
    )
    q = res.questions[0]
    assert q.first_correct_student is None and q.answered_count == 0
    assert all(o.percentage == 0 for o in q.options)
