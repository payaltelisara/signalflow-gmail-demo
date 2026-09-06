from celery import Celery

from .config import get_settings

settings = get_settings()
celery = Celery("signalflow", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="imports",
    imports=("app.tasks",),
    task_routes={"app.tasks.generate_ai_suggestion": {"queue": "ai"}},
    beat_schedule={
        "dispatch-outbox": {"task": "app.tasks.dispatch_outbox", "schedule": 5.0},
        "deliver-scheduled-messages": {"task": "app.tasks.deliver_scheduled_messages", "schedule": 60.0},
        "poll-connected-gmail-mailboxes": {"task": "app.tasks.poll_connected_gmail_mailboxes", "schedule": float(settings.gmail_poll_interval_seconds)},
    },
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
