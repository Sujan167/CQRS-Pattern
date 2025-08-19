import logging
from typing import Optional
from sqlalchemy import select
from app.db.models import Task
from app.db.schemas import TaskOut
from app.db.write_db import async_write_session
from app.tasks import sync_task_updated


logger = logging.getLogger(__name__)


async def update_task(task_id: str, title: Optional[str] = None, description: Optional[str] = None, is_completed: Optional[bool] = None):
    async with async_write_session() as session:
        async with session.begin():
            result = await session.execute(select(Task).where(Task.id == task_id))
            task: Optional[Task] = result.scalar_one_or_none()
            if not task:
                return None

            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if is_completed is not None:
                task.is_completed = is_completed

    task_dict = TaskOut.from_orm(task).model_dump(mode="json")
    sync_task_updated.delay(task_dict)
    logger.info(f"Published update for task {task_id}")
    return task_dict


