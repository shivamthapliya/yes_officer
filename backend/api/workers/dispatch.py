"""Thin, import-light façade for publishing Celery tasks by name.

Services call these instead of importing task modules, which keeps the API free
of worker imports and makes publishing trivial to stub in tests.
"""

import logging
from datetime import datetime

from api.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

ANALYZE_BATCH = "api.workers.tasks.analyze_batch"
PERSIST_RESULTS = "api.workers.tasks.persist_poll_results"
AUTO_END_POLL = "api.workers.tasks.auto_end_poll"


def publish_analyze(batch_id: str) -> None:
    # task_id == batch_id: duplicate publishes (e.g. from the recovery sweeper) are harmless.
    celery_app.send_task(ANALYZE_BATCH, args=[batch_id], task_id=batch_id)


def publish_persist(poll_id: str) -> None:
    celery_app.send_task(PERSIST_RESULTS, args=[poll_id])


def schedule_auto_end(poll_id: str, eta: datetime) -> None:
    celery_app.send_task(AUTO_END_POLL, args=[poll_id], eta=eta)


def revoke(task_ids: list[str]) -> None:
    for task_id in task_ids:
        try:
            celery_app.control.revoke(task_id)
        except Exception:  # noqa: BLE001 - best-effort only; workers re-check state
            logger.warning("Could not revoke task %s", task_id, exc_info=True)
