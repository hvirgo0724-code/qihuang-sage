"""Celery 应用（Redis broker + result backend）。"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "tcm",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=86400,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)

# Producer instrumentation propagates W3C context into broker messages.
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from celery.signals import worker_process_init, worker_process_shutdown
CeleryInstrumentor().instrument()


@worker_process_init.connect
def init_worker_telemetry(**kwargs):
    from app.core.logging import setup_logging
    from app.core.tracing import init_tracing
    setup_logging()
    init_tracing("tcm-worker")


@worker_process_shutdown.connect
def stop_worker_telemetry(**kwargs):
    from app.core.tracing import shutdown_tracing
    shutdown_tracing()


celery_app.conf.beat_schedule = {
    "expire-agent-memory": {"task": "tasks.expire_memory", "schedule": 3600.0},
}
