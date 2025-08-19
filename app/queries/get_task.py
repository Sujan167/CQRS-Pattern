from sqlalchemy.future import select
from app.db.read_db import async_read_session
from app.db.models import Task
from app.cache.redis_cache import (
    cache_add_task_async,
    cache_get_all_ids_async,
    cache_get_tasks_by_ids_async,
    cache_set_index_async,
    cache_remove_task_async,
)
import logging

logger = logging.getLogger(__name__)


async def get_task():
    # 1) Try to serve from cache using index + bulk gets
    task_ids = await cache_get_all_ids_async()
    if task_ids:
        cached, missing_ids = await cache_get_tasks_by_ids_async(task_ids)
        # If some are missing due to TTL, refill them from DB
        if missing_ids:
            async with async_read_session() as session:
                result = await session.execute(select(Task).where(Task.id.in_(missing_ids)))
                missing_tasks = result.scalars().all()
                found_ids = set()
                for task in missing_tasks:
                    task_data = {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "is_completed": task.is_completed,
                        "created_at": task.created_at.isoformat(),
                    }
                    found_ids.add(task.id)
                    await cache_add_task_async(task_data)
                    cached.append(task_data)
                # Clean up index for IDs that no longer exist in DB
                for mid in missing_ids:
                    if mid not in found_ids:
                        await cache_remove_task_async(mid)
        if cached:
            logger.debug(f"Cache hit: {len(cached)} tasks (with refills: {len(task_ids) - len(missing_ids)})")
            return cached

    # 2) Cache miss: fill both index and items from DB
    async with async_read_session() as session:
        result = await session.execute(select(Task))
        tasks = result.scalars().all()
        if not tasks:
            return []
        tasks_data = []
        ids = []
        for task in tasks:
            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "is_completed": task.is_completed,
                "created_at": task.created_at.isoformat(),
            }
            ids.append(task.id)
            tasks_data.append(task_data)
        await cache_set_index_async(ids)
        for task_data in tasks_data:
            await cache_add_task_async(task_data)
        logger.info(f"Fetched {len(tasks_data)} tasks from DB and primed cache.")
        return tasks_data
