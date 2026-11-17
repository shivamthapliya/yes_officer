"""Celery tasks: AI batch analysis, result persistence, flush/recovery sweepers."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from redis import Redis
from sqlalchemy import update

from api.config.settings import settings
from api.db.session import SessionLocal
from api.enums import (
    TERMINAL_BATCH_STATUSES,
    AnalysisStatus,
    BatchStatus,
    BatchTrigger,
    PollStatus,
    ResultsStatus,
)
from api.models import Poll
from api.realtime.live_state import LiveStateStore, now_ms
from api.repositories.ai_repo import BatchRepository, InsightRepository
from api.repositories.poll_repo import AnswerRepository, PollParticipantRepository, PollRepository
from api.services.batch_dispatch_service import dispatch_batches, register_and_publish
from api.services.results_service import ms_to_dt
from api.workers import dispatch
from api.workers.celery_app import celery_app
from api.workers.llm_client import (
    AnalysisContext,
    AnalysisOutput,
    ContextMessage,
    ContextOption,
    ContextQuestion,
    PermanentLLMError,
    TransientLLMError,
    get_analyzer,
    is_presentable,
)

logger = logging.getLogger(__name__)
LIVE_POLL_STATUSES = (PollStatus.ACTIVE, PollStatus.COMPLETED)
OPTION_LETTERS = "ABCDEF"

_live: LiveStateStore | None = None


def live_state() -> LiveStateStore:
    global _live
    if _live is None:
        _live = LiveStateStore(Redis.from_url(settings.REDIS_URL))
    return _live


def _internal_post(path: str, payload: dict | None = None) -> httpx.Response:
    return httpx.post(
        f"{settings.INTERNAL_API_BASE_URL}{settings.API_PREFIX}/internal{path}",
        json=payload or {},
        headers={"X-Internal-Secret": settings.INTERNAL_SHARED_SECRET},
        timeout=10,
    )


def _notify_insights(poll_id: str, question_id: str | None, version: int) -> None:
    try:
        _internal_post("/events/insights-updated", {"poll_id": poll_id, "question_id": question_id, "version": version})
    except httpx.HTTPError:
        logger.warning("Could not notify API about insights for poll %s", poll_id, exc_info=True)


# ---------------------------------------------------------------- context
def build_context(poll: Poll, messages: list[dict]) -> tuple[AnalysisContext, dict[str, dict[str, str]]]:
    """Builds the LLM context with opaque refs, plus the ref → id maps to decode output."""
    q_refs: dict[str, str] = {}
    o_refs: dict[str, tuple[str, str]] = {}
    questions = []
    for i, q in enumerate(poll.questions):
        qref = f"Q{i + 1}"
        q_refs[str(q.id)] = qref
        options = []
        for j, o in enumerate(q.options):
            oref = f"{qref}-{OPTION_LETTERS[j]}"
            o_refs[oref] = (str(o.id), str(q.id))
            options.append(ContextOption(ref=oref, label=o.label))
        questions.append(ContextQuestion(ref=qref, prompt=q.prompt, options=options))

    s_refs: dict[str, str] = {}
    context_messages = []
    for m in messages:
        sref = s_refs.setdefault(m["student_id"], f"S{len(s_refs) + 1}")
        context_messages.append(
            ContextMessage(student_ref=sref, question_ref=q_refs.get(m.get("question_id") or ""), content=m["content"])
        )
    maps = {
        "questions": {v: k for k, v in q_refs.items()},
        "students": {v: k for k, v in s_refs.items()},
        "options": {k: v[0] for k, v in o_refs.items()},
        "option_question": {k: v[1] for k, v in o_refs.items()},
    }
    return AnalysisContext(poll_title=poll.title, questions=questions, messages=context_messages), maps


def normalize_topic_key(key: str | None) -> str | None:
    if not key:
        return None
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in key.strip().lower())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:200] or None


def _maybe_complete_analysis(poll_id: str) -> None:
    """FINALIZING → COMPLETE once no batch is pending; bumps the version so clients refresh."""
    live = live_state()
    if live.inflight_count(poll_id) or live.pending_count(poll_id):
        return
    with SessionLocal() as db:
        pid = uuid.UUID(poll_id)
        if BatchRepository.open_count(db, pid):
            return
        result = db.execute(
            update(Poll)
            .where(Poll.id == pid, Poll.status == PollStatus.COMPLETED, Poll.analysis_status == AnalysisStatus.FINALIZING)
            .values(analysis_status=AnalysisStatus.COMPLETE, insights_version=Poll.insights_version + 1)
            .returning(Poll.insights_version)
        ).first()
        db.commit()
    if result is not None:
        _notify_insights(poll_id, None, int(result[0]))


def _finish_failed(batch_id: str, poll_id: str, status: BatchStatus, error: str) -> None:
    with SessionLocal() as db:
        BatchRepository.mark_terminal(db, uuid.UUID(batch_id), status, error, datetime.now(UTC))
        db.commit()
    live_state().ack_batch(poll_id, batch_id)
    _maybe_complete_analysis(poll_id)


# ---------------------------------------------------------------- analyze
@celery_app.task(bind=True, name="api.workers.tasks.analyze_batch", max_retries=settings.BATCH_MAX_ATTEMPTS - 1)
def analyze_batch(self, batch_id: str) -> None:
    live = live_state()
    bid = uuid.UUID(batch_id)
    with SessionLocal() as db:
        batch = BatchRepository.get(db, bid)
        if batch is None:
            return
        poll_id = str(batch.poll_id)
        if batch.status in TERMINAL_BATCH_STATUSES:
            live.ack_batch(poll_id, batch_id)
            return
        poll = PollRepository.get(db, batch.poll_id, with_questions=True)
        if poll is None or poll.status not in LIVE_POLL_STATUSES:  # check 1: before the LLM call
            BatchRepository.mark_terminal(db, bid, BatchStatus.CANCELLED, None, datetime.now(UTC))
            db.commit()
            live.ack_batch(poll_id, batch_id)
            return
        BatchRepository.mark_processing(db, bid, datetime.now(UTC))
        db.commit()
        messages = live.get_batch(poll_id, batch_id)
        if not messages:
            db.close()
            _finish_failed(batch_id, poll_id, BatchStatus.FAILED, "Batch payload missing from Redis")
            return
        context, maps = build_context(poll, messages)
        batch_question_id = str(batch.question_id) if batch.question_id else None

    try:
        output = get_analyzer().analyze(context)
    except TransientLLMError as exc:
        with SessionLocal() as db:
            BatchRepository.record_error(db, bid, f"transient: {exc}")
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries)) from exc
        _finish_failed(batch_id, poll_id, BatchStatus.FAILED, f"gave up after retries: {exc}")
        return
    except PermanentLLMError as exc:
        _finish_failed(batch_id, poll_id, BatchStatus.FAILED, str(exc))
        return

    version = _merge(batch_id, poll_id, output, maps)
    live.ack_batch(poll_id, batch_id)
    if version is not None:
        _notify_insights(poll_id, batch_question_id, version)
    _maybe_complete_analysis(poll_id)


def _merge(batch_id: str, poll_id: str, output: AnalysisOutput, maps: dict) -> int | None:
    """Exactly-once merge. Returns the new insights_version, or None if discarded."""
    now = datetime.now(UTC)
    with SessionLocal() as db:
        pid = uuid.UUID(poll_id)
        poll = PollRepository.get_for_update(db, pid)  # check 2; serializes against cancel + other merges
        if poll is None or poll.status not in LIVE_POLL_STATUSES:
            BatchRepository.mark_terminal(db, uuid.UUID(batch_id), BatchStatus.CANCELLED, None, now)
            db.commit()
            return None
        if not BatchRepository.claim_success(db, uuid.UUID(batch_id), output.model_dump(mode="json"), now):
            db.rollback()  # already merged by a duplicate run, or cancelled
            return None
        version = PollRepository.bump_insights_version(db, pid)
        kept = [item for item in output.insights if is_presentable(item)]
        if len(kept) < len(output.insights):
            logger.warning(
                "Dropped %d insight(s) from batch %s that failed output checks",
                len(output.insights) - len(kept), batch_id,
            )
        for item in kept:
            question_id = maps["questions"].get(item.question_ref or "")
            option_id = maps["options"].get(item.option_ref or "")
            if option_id and question_id and maps["option_question"].get(item.option_ref) != question_id:
                option_id = None  # option must belong to the referenced question
            if option_id and not question_id:
                question_id = maps["option_question"].get(item.option_ref)
            student_id = maps["students"].get(item.student_ref or "")
            InsightRepository.merge(
                db,
                poll_id=pid,
                question_id=uuid.UUID(question_id) if question_id else None,
                student_id=uuid.UUID(student_id) if student_id else None,
                category=item.category,
                topic_label=item.topic_label.strip()[:200] or "Untitled",
                normalized_topic_key=normalize_topic_key(item.topic_key),
                summary=item.summary.strip()[:2000] or item.topic_label,
                referenced_option_id=uuid.UUID(option_id) if option_id else None,
                confidence=Decimal(str(round(min(max(item.confidence, 0.0), 1.0), 2))),
                support_count=max(1, min(item.support_count, 50)),
                observed_at=now,
                version=version,
            )
        db.commit()
        return version


# ---------------------------------------------------------------- finalize
@celery_app.task(name="api.workers.tasks.persist_poll_results")
def persist_poll_results(poll_id: str) -> None:
    live = live_state()
    pid = uuid.UUID(poll_id)
    with SessionLocal() as db:
        poll = PollRepository.get(db, pid)
        if poll is None or poll.status != PollStatus.COMPLETED:
            return
        dispatch_batches(db, live, poll_id, BatchTrigger.POLL_END, min_count=1)  # final AI flush

        if poll.results_status != ResultsStatus.PERSISTED:
            snap = live.get_results(poll_id)
            if snap is None:
                PollRepository.update_fields(db, pid, results_status=ResultsStatus.FAILED)
                db.commit()
                logger.error("Results snapshot for poll %s is gone; cannot persist", poll_id)
            else:
                AnswerRepository.bulk_insert(db, [
                    {
                        "id": uuid.uuid4(), "poll_id": pid, "question_id": uuid.UUID(a["question_id"]),
                        "student_id": uuid.UUID(a["student_id"]), "selected_option_id": uuid.UUID(a["option_id"]),
                        "is_correct": bool(a["is_correct"]), "received_at": ms_to_dt(a["ts_ms"]),
                        "accept_seq": int(a["seq"]),
                    }
                    for a in snap["answers"]
                ])
                PollParticipantRepository.bulk_insert(db, pid, [uuid.UUID(s) for s in snap["participant_ids"]])
                PollRepository.update_fields(db, pid, results_status=ResultsStatus.PERSISTED)
                db.commit()
                live.clear_after_persist(poll_id)
    _maybe_complete_analysis(poll_id)


@celery_app.task(bind=True, name="api.workers.tasks.auto_end_poll", max_retries=5)
def auto_end_poll(self, poll_id: str) -> None:
    try:
        _internal_post(f"/polls/{poll_id}/auto-end").raise_for_status()
    except httpx.HTTPError as exc:
        raise self.retry(exc=exc, countdown=5) from exc


# ---------------------------------------------------------------- sweepers
@celery_app.task(name="api.workers.tasks.flush_due_buffers")
def flush_due_buffers() -> None:
    """Time-based flush so low-volume polls still get analytics."""
    live = live_state()
    cutoff = now_ms() - settings.CHAT_FLUSH_INTERVAL_SECONDS * 1000
    for poll_id in live.due_flush_polls(cutoff):
        with SessionLocal() as db:
            dispatch_batches(db, live, poll_id, BatchTrigger.INTERVAL, min_count=1)


@celery_app.task(name="api.workers.tasks.recover_batches")
def recover_batches() -> None:
    live = live_state()
    now = datetime.now(UTC)
    cutoff = now_ms() - settings.BATCH_RECOVERY_AGE_SECONDS * 1000
    stuck_before = now - timedelta(minutes=5)

    for poll_id, batch_id in list(live.iter_inflight(cutoff)):
        with SessionLocal() as db:
            batch = BatchRepository.get(db, uuid.UUID(batch_id))
            if batch is None:
                messages = live.get_batch(poll_id, batch_id)
                if not messages:
                    live.ack_batch(poll_id, batch_id)
                    continue
                register_and_publish(
                    db, poll_id=poll_id, batch_id=batch_id, messages=messages,
                    trigger=BatchTrigger.INTERVAL, claimed_at=now,
                )
            elif batch.status in TERMINAL_BATCH_STATUSES:
                live.ack_batch(poll_id, batch_id)
            elif batch.status == BatchStatus.PENDING or batch.updated_at < stuck_before:
                dispatch.publish_analyze(batch_id)

    with SessionLocal() as db:
        for pid in PollRepository.stale_processing_results(db, now - timedelta(minutes=1)):
            dispatch.publish_persist(str(pid))
        overdue = PollRepository.overdue_active(db, now - timedelta(seconds=5))
    for pid in overdue:
        try:
            _internal_post(f"/polls/{pid}/auto-end")
        except httpx.HTTPError:
            logger.warning("Could not auto-end overdue poll %s", pid, exc_info=True)
