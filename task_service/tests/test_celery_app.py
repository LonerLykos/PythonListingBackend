from app.celery_app import app
from app.config import settings
from celery.schedules import crontab


def test_celery_configuration():
    assert app.conf.broker_url == settings.rabbitmq_url
    assert app.conf.task_serializer == "json"
    assert app.conf.timezone == "UTC"
    assert "clean-expired-tokens" in app.conf.beat_schedule
    assert app.conf.beat_schedule["clean-expired-tokens"]["task"] == "app.tasks.clean_expired_tokens"
    assert app.conf.beat_schedule["clean-expired-tokens"]["schedule"] == crontab(minute="*/10")
