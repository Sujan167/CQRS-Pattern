from datetime import datetime
import uuid
import logging
from typing import List, Optional
from sqlalchemy.future import select
from app.db.models import Task
from app.db.schemas import TaskCreateRequest, TaskOut
from app.db.write_db import async_write_session
from app.db.read_db import async_read_session
from app.cache.redis_cache import (
    cache_add_task_async,
    cache_get_all_ids_async,
    cache_get_tasks_by_ids_async,
    cache_set_index_async,
    cache_remove_task_async,
)
from app.tasks import sync_task_created, sync_task_deleted, sync_task_updated

logger = logging.getLogger(__name__)


class TaskService:
    """Service layer for all task CRUD operations"""
    
    @staticmethod
    async def create_task(payload: TaskCreateRequest) -> dict:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=payload.title,
            description=payload.description,
            is_completed=payload.is_completed,
        )

        logger.info(
            f'Task Created\nID: {task.id}\nTitle: {task.title}\nDescription: {task.description}'
        )

        async with async_write_session() as session:
            async with session.begin():
                session.add(task)

        logger.info(f"Task {task.id} created in write DB.")

        # Convert task to JSON-serializable dict for Celery
        task_dict = TaskOut.model_validate(task).model_dump(mode="json")
        logger.debug(f'task_dict for Celery: {task_dict}')

        # Publish to Celery to update read DB and cache
        sync_task_created.delay(task_dict)

        logger.info(f"Task {task.id} published to read DB sync queue.")

        return task_dict
    
    @staticmethod
    async def get_all_tasks() -> List[dict]:
        """Get all tasks with caching"""
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
                            "updated_at": task.updated_at.isoformat(),
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
                    "updated_at": task.updated_at.isoformat(),
                }
                ids.append(task.id)
                tasks_data.append(task_data)
            await cache_set_index_async(ids)
            for task_data in tasks_data:
                await cache_add_task_async(task_data)
            logger.info(f"Fetched {len(tasks_data)} tasks from DB and primed cache.")
            return tasks_data
    
    @staticmethod
    async def get_task_by_id(task_id: str) -> Optional[dict]:
        """Get a specific task by ID"""
        async with async_read_session() as session:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                return {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "is_completed": task.is_completed,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                }
            return None
    
    @staticmethod
    async def update_task(
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_completed: Optional[bool] = None
    ) -> Optional[dict]:
        """Update a specific task by ID"""
        async with async_write_session() as session:
            async with session.begin():
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if not task:
                    return None
                
                if title is not None:
                    task.title = title
                if description is not None:
                    task.description = description
                if is_completed is not None:
                    task.is_completed = is_completed
                
                # Flush to get updated data
                await session.flush()
                
                # Convert to dict for return
                task_dict = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "is_completed": task.is_completed,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                
                logger.info(f"Task {task_id} updated: {task_dict}")
                # Publish to Celery to update read DB and cache
                sync_task_updated.delay(task_dict)
                return task_dict
    
    @staticmethod
    async def delete_task(task_id: str) -> bool:
        """Delete a specific task by ID"""
        async with async_write_session() as session:
            async with session.begin():
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if not task:
                    return False
                
                await session.delete(task)
                logger.info(f"Task {task_id} deleted from write DB.")
                sync_task_deleted.delay(task_id)
                return True
