from celery import Celery
from celery.schedules import crontab
from app.config import settings

app = Celery(
    "task_service",
    broker=settings.rabbitmq_url,
    include=["app.tasks"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=30,
)

app.conf.beat_schedule = {
    "clean-expired-tokens": {
        "task": "app.tasks.clean_expired_tokens",
        "schedule": crontab(minute="*/10"),
    },
    "fetch-exchange-rates": {
        "task": "app.tasks.fetch_exchange_rates",
        "schedule": crontab(minute=0, hour=0),
    },
}
