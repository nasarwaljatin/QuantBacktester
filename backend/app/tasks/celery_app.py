# backend/app/tasks/celery_app.py
"""Celery application configuration."""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "quantbacktester",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.backtest_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,  # Results expire after 1 hour
)
