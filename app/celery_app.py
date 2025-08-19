from celery import Celery
import os

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    include=["app.tasks"]
)

# Optional: You can configure serialization, timeouts etc. here
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None  # or redis if you need result tracking
)
