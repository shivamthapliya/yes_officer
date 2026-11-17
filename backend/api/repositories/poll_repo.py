"""Poll, question, option, answer and participant data access."""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from api.enums import PollStatus
from api.models import (
    Poll,
    PollParticipant,
    PollQuestion,
    QuestionOption,
    Room,
    StudentAnswer,
)


class PollRepository:
    @staticmethod
    def get(db: Session, poll_id: uuid.UUID, *, with_questions: bool = False) -> Poll | None:
        stmt = select(Poll).where(Poll.id == poll_id)
        if with_questions:
            stmt = stmt.options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        return db.scalar(stmt)

    @staticmethod
    def get_for_update(db: Session, poll_id: uuid.UUID) -> Poll | None:
        return db.scalar(select(Poll).where(Poll.id == poll_id).with_for_update())

    @staticmethod
    def get_status_for_share(db: Session, poll_id: uuid.UUID) -> PollStatus | None:
        return db.scalar(select(Poll.status).where(Poll.id == poll_id).with_for_update(read=True))

    @staticmethod
    def create(db: Session, *, room_id: uuid.UUID, title: str, time_limit_seconds: int) -> Poll:
        poll = Poll(room_id=room_id, title=title, time_limit_seconds=time_limit_seconds)
        db.add(poll)
        db.flush()
        return poll

    @staticmethod
    def list_for_room(
        db: Session, room_id: uuid.UUID, *, status: PollStatus | None, offset: int, limit: int
    ) -> tuple[list[tuple[Poll, int]], int]:
        qcount = (
            select(PollQuestion.poll_id, func.count().label("n")).group_by(PollQuestion.poll_id).subquery()
        )
        base = select(Poll, func.coalesce(qcount.c.n, 0)).outerjoin(qcount, qcount.c.poll_id == Poll.id).where(
            Poll.room_id == room_id
        )
        if status is not None:
            base = base.where(Poll.status == status)
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = db.execute(base.order_by(Poll.created_at.desc()).offset(offset).limit(limit)).all()
        return [(r[0], int(r[1])) for r in rows], int(total)

    @staticmethod
    def question_count(db: Session, poll_id: uuid.UUID) -> int:
        return db.scalar(select(func.count()).where(PollQuestion.poll_id == poll_id)) or 0

    @staticmethod
    def transition(db: Session, poll_id: uuid.UUID, expected: PollStatus, **values) -> bool:
        """Conditional state transition: UPDATE … WHERE status = :expected."""
        result = db.execute(
            update(Poll).where(Poll.id == poll_id, Poll.status == expected).values(**values)
        )
        return bool(result.rowcount)

    @staticmethod
    def update_fields(db: Session, poll_id: uuid.UUID, **values) -> None:
        db.execute(update(Poll).where(Poll.id == poll_id).values(**values))

    @staticmethod
    def bump_insights_version(db: Session, poll_id: uuid.UUID) -> int:
        return db.scalar(
            update(Poll).where(Poll.id == poll_id).values(insights_version=Poll.insights_version + 1)
            .returning(Poll.insights_version)
        )

    @staticmethod
    def delete(db: Session, poll: Poll) -> None:
        db.delete(poll)
        db.flush()

    @staticmethod
    def delete_subtree_for_cancel(db: Session, poll_id: uuid.UUID) -> None:
        # Questions cascade to options, answers, and question-scoped insights.
        db.execute(delete(PollQuestion).where(PollQuestion.poll_id == poll_id))
        db.execute(delete(PollParticipant).where(PollParticipant.poll_id == poll_id))
        from api.models import AIInsight  # local import keeps module graph flat

        db.execute(delete(AIInsight).where(AIInsight.poll_id == poll_id))

    @staticmethod
    def stale_processing_results(db: Session, ended_before: datetime) -> list[uuid.UUID]:
        from api.enums import ResultsStatus

        return list(
            db.scalars(
                select(Poll.id).where(
                    Poll.status == PollStatus.COMPLETED,
                    Poll.results_status == ResultsStatus.PROCESSING,
                    Poll.ended_at < ended_before,
                )
            )
        )

    @staticmethod
    def unpersisted_completed_in_joined_rooms(db: Session, student_id: uuid.UUID) -> list[tuple[Poll, Room]]:
        from api.enums import ResultsStatus
        from api.models import RoomParticipant

        rows = db.execute(
            select(Poll, Room)
            .join(Room, Room.id == Poll.room_id)
            .join(RoomParticipant, RoomParticipant.room_id == Room.id)
            .where(
                RoomParticipant.student_id == student_id,
                Poll.status == PollStatus.COMPLETED,
                Poll.results_status != ResultsStatus.PERSISTED,
            )
            .order_by(Poll.ended_at.desc())
            .limit(20)
        ).all()
        return [(r[0], r[1]) for r in rows]

    @staticmethod
    def overdue_active(db: Session, now: datetime) -> list[uuid.UUID]:
        return list(
            db.scalars(select(Poll.id).where(Poll.status == PollStatus.ACTIVE, Poll.deadline_at <= now))
        )


class QuestionRepository:
    @staticmethod
    def get(db: Session, question_id: uuid.UUID) -> PollQuestion | None:
        return db.scalar(
            select(PollQuestion)
            .where(PollQuestion.id == question_id)
            .options(selectinload(PollQuestion.options))
        )

    @staticmethod
    def next_position(db: Session, poll_id: uuid.UUID) -> int:
        current = db.scalar(select(func.max(PollQuestion.position)).where(PollQuestion.poll_id == poll_id))
        return 0 if current is None else current + 1

    @staticmethod
    def add(db: Session, *, poll_id: uuid.UUID, position: int, prompt: str, options: list[tuple[str, bool]]) -> PollQuestion:
        question = PollQuestion(poll_id=poll_id, position=position, prompt=prompt)
        question.options = [
            QuestionOption(position=i, label=label, is_correct=correct)
            for i, (label, correct) in enumerate(options)
        ]
        db.add(question)
        db.flush()
        return question

    @staticmethod
    def replace_options(db: Session, question: PollQuestion, options: list[tuple[str, bool]]) -> None:
        question.options.clear()
        db.flush()
        question.options.extend(
            QuestionOption(position=i, label=label, is_correct=correct)
            for i, (label, correct) in enumerate(options)
        )
        db.flush()

    @staticmethod
    def list_ids(db: Session, poll_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            db.scalars(select(PollQuestion.id).where(PollQuestion.poll_id == poll_id).order_by(PollQuestion.position))
        )

    @staticmethod
    def set_positions(db: Session, ordered_ids: list[uuid.UUID]) -> None:
        # The (poll_id, position) unique constraint is DEFERRABLE INITIALLY DEFERRED,
        # so intermediate duplicates inside the transaction are fine.
        for position, qid in enumerate(ordered_ids):
            db.execute(update(PollQuestion).where(PollQuestion.id == qid).values(position=position))

    @staticmethod
    def compact_positions(db: Session, poll_id: uuid.UUID) -> None:
        QuestionRepository.set_positions(db, QuestionRepository.list_ids(db, poll_id))


class AnswerRepository:
    @staticmethod
    def bulk_insert(db: Session, rows: list[dict]) -> None:
        if rows:
            db.execute(insert(StudentAnswer).values(rows).on_conflict_do_nothing())

    @staticmethod
    def for_poll(db: Session, poll_id: uuid.UUID) -> list[StudentAnswer]:
        return list(db.scalars(select(StudentAnswer).where(StudentAnswer.poll_id == poll_id)))

    @staticmethod
    def for_student(db: Session, poll_id: uuid.UUID, student_id: uuid.UUID) -> list[StudentAnswer]:
        return list(
            db.scalars(
                select(StudentAnswer).where(StudentAnswer.poll_id == poll_id, StudentAnswer.student_id == student_id)
            )
        )


class PollParticipantRepository:
    @staticmethod
    def bulk_insert(db: Session, poll_id: uuid.UUID, student_ids: list[uuid.UUID]) -> None:
        if student_ids:
            db.execute(
                insert(PollParticipant)
                .values([{"poll_id": poll_id, "student_id": s} for s in student_ids])
                .on_conflict_do_nothing()
            )

    @staticmethod
    def student_ids(db: Session, poll_id: uuid.UUID) -> list[uuid.UUID]:
        return list(db.scalars(select(PollParticipant.student_id).where(PollParticipant.poll_id == poll_id)))

    @staticmethod
    def is_participant(db: Session, poll_id: uuid.UUID, student_id: uuid.UUID) -> bool:
        return (
            db.scalar(
                select(PollParticipant.poll_id).where(
                    PollParticipant.poll_id == poll_id, PollParticipant.student_id == student_id
                )
            )
            is not None
        )

    @staticmethod
    def completed_polls_for_student(
        db: Session, student_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[tuple[Poll, Room]], int]:
        base = (
            select(Poll, Room)
            .join(PollParticipant, PollParticipant.poll_id == Poll.id)
            .join(Room, Room.id == Poll.room_id)
            .where(PollParticipant.student_id == student_id, Poll.status == PollStatus.COMPLETED)
        )
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = db.execute(base.order_by(Poll.ended_at.desc()).offset(offset).limit(limit)).all()
        return [(r[0], r[1]) for r in rows], int(total)
