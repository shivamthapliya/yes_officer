from celery import Celery

from api.config.settings import settings

celery_app = Celery("yes_officer", broker=settings.CELERY_BROKER_URL, include=["api.workers.tasks"])

celery_app.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # Must exceed the longest ETA we schedule (auto-end at most 5 min out).
    broker_transport_options={"visibility_timeout": 3600},
    beat_schedule={
        "flush-due-chat-buffers": {
            "task": "api.workers.tasks.flush_due_buffers",
            "schedule": float(settings.CHAT_FLUSH_INTERVAL_SECONDS),
        },
        "recover-batches": {
            "task": "api.workers.tasks.recover_batches",
            "schedule": float(settings.BATCH_RECOVERY_INTERVAL_SECONDS),
        },
    },
)
