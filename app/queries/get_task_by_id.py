from sqlalchemy import select
from app.db.read_db import async_read_session
from app.db.models import Task
from app.cache.redis_cache import (
    cache_add_task_async,
)


async def get_task_by_id(task_id: str):
    async with async_read_session() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None
        data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "is_completed": task.is_completed,
            "created_at": task.created_at.isoformat(),
        }
        await cache_add_task_async(data)
        return data


