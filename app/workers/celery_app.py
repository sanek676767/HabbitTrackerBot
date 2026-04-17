"""Конфигурация Celery-приложения для напоминаний и сводок."""

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "habit_tracker_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        # Обе задачи запускаются каждую минуту, потому что окна отправки
        # сравниваются с локальным временем пользователя с точностью до минуты.
        "dispatch-habit-reminders-every-minute": {
            "task": "app.workers.tasks.dispatch_habit_reminders",
            "schedule": 60.0,
        },
        "dispatch-progress-summaries-every-minute": {
            "task": "app.workers.tasks.dispatch_progress_summaries",
            "schedule": 60.0,
        }
    },
)
