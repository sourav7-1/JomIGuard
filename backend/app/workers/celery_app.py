from celery import Celery

from app.core.config import settings

# no result backend: a document's status lives in Postgres
celery_app = Celery("jomiguard", broker=settings.celery_broker_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_acks_late=True,  # a task lost with its worker is redelivered
    worker_prefetch_multiplier=1,  # long OCR/LLM tasks: take one at a time
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    # Gemini's free tier rate-limits: one task at a time
    worker_concurrency=1 if settings.llm_provider == "gemini" else 2,
)
