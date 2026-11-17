"""Claim chat batches from Redis and hand them to Celery without losing any.

Handoff: (1) `claim_batch` atomically moves messages into `chat:batch:{id}` and
records the id as in-flight; (2) the batch row is inserted (PENDING); (3) the
task is published with task_id == batch_id. A crash between steps leaves the
batch in Redis + in-flight, and the `recover_batches` sweeper republishes it.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.config.settings import settings
from api.enums import BatchTrigger
from api.realtime.live_state import LiveStateStore
from api.repositories.ai_repo import BatchRepository
from api.workers import dispatch

logger = logging.getLogger(__name__)


def batch_question_id(messages: list[dict]) -> uuid.UUID | None:
    qids = {m.get("question_id") for m in messages}
    if len(qids) == 1 and (qid := next(iter(qids))):
        return uuid.UUID(qid)
    return None


def register_and_publish(
    db: Session, *, poll_id: str, batch_id: str, messages: list[dict], trigger: BatchTrigger, claimed_at: datetime
) -> None:
    try:
        BatchRepository.create_if_missing(
            db,
            batch_id=uuid.UUID(batch_id),
            poll_id=uuid.UUID(poll_id),
            question_id=batch_question_id(messages),
            trigger=trigger,
            message_count=len(messages),
            claimed_at=claimed_at,
        )
        db.commit()
    except IntegrityError:
        # The poll's subtree vanished (cancelled mid-claim); the batch is moot.
        db.rollback()
        logger.info("Dropping batch %s for poll %s: poll no longer exists in full", batch_id, poll_id)
        return
    try:
        dispatch.publish_analyze(batch_id)
    except Exception:  # noqa: BLE001 - the recovery sweeper republishes in-flight batches
        logger.warning("Publishing batch %s failed; recovery will retry", batch_id, exc_info=True)


def dispatch_batches(
    db: Session, live: LiveStateStore, poll_id: str, trigger: BatchTrigger, *, min_count: int = 1
) -> list[str]:
    """Claim and publish batches until fewer than `min_count` messages remain."""
    published: list[str] = []
    while True:
        claimed = live.claim_batch(poll_id, min_count)
        if claimed is None:
            return published
        batch_id, messages = claimed
        register_and_publish(
            db, poll_id=poll_id, batch_id=batch_id, messages=messages, trigger=trigger,
            claimed_at=datetime.now(UTC),
        )
        published.append(batch_id)


def dispatch_threshold(db: Session, live: LiveStateStore, poll_id: str) -> list[str]:
    return dispatch_batches(db, live, poll_id, BatchTrigger.THRESHOLD, min_count=settings.CHAT_BATCH_SIZE)
