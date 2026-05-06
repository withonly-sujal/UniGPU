from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "unigpu_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,  # Celery 6.0+ compatibility
    beat_schedule={
        "check-heartbeats-every-30s": {
            "task": "app.worker.tasks.check_heartbeats",
            "schedule": 30.0,
        },
    },
)
