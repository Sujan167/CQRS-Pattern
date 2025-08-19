from app.celery_app import celery_app
from app.db.read_db_sync import SyncSessionLocal
from app.db.models import Task
from app.cache.redis_cache import (
    cache_add_task_sync,
    cache_remove_task_sync,
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _normalize_task_datetime(task_data: dict) -> dict:
    if isinstance(task_data.get("created_at"), str):
        task_data["created_at"] = datetime.fromisoformat(task_data["created_at"])
    return task_data


@celery_app.task(name="sync_task_created")
def sync_task_created(task_data: dict):
    logger.info(f"🔄 Sync create into read DB: {task_data}")
    db = SyncSessionLocal()
    try:
        task_data = _normalize_task_datetime(task_data)
        task = Task(**task_data)
        db.merge(task)
        db.commit()
        cache_add_task_sync(task_data)
        logger.info(f"✅ Created task synced: {task.id}")
    except Exception as e:
        logger.error(f"❌ Error syncing create: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="sync_task_updated")
def sync_task_updated(task_data: dict):
    logger.info(f"🔄 Sync update into read DB: {task_data}")
    db = SyncSessionLocal()
    try:
        task_data = _normalize_task_datetime(task_data)
        task = Task(**task_data)
        db.merge(task)
        db.commit()
        cache_add_task_sync(task_data)
        logger.info(f"✅ Updated task synced: {task.id}")
    except Exception as e:
        logger.error(f"❌ Error syncing update: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="sync_task_deleted")
def sync_task_deleted(task_id: str):
    logger.info(f"🔄 Sync delete from read DB: {task_id}")
    db = SyncSessionLocal()
    try:
        obj = db.get(Task, task_id)
        if obj:
            db.delete(obj)
            db.commit()
        cache_remove_task_sync(task_id)
        logger.info(f"✅ Deleted task synced: {task_id}")
    except Exception as e:
        logger.error(f"❌ Error syncing delete: {e}")
        db.rollback()
    finally:
        db.close()
