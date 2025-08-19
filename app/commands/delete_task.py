import logging
from sqlalchemy import select
from app.db.write_db import async_write_session
from app.db.models import Task
from app.tasks import sync_task_deleted


logger = logging.getLogger(__name__)


async def delete_task(task_id: str) -> bool:
    async with async_write_session() as session:
        async with session.begin():
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return False
            await session.delete(task)
    sync_task_deleted.delay(task_id)
    logger.info(f"Published delete for task {task_id}")
    return True


