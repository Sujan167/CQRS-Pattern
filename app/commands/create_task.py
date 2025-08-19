import uuid
import logging
from app.db.models import Task
from app.db.schemas import TaskCreateRequest, TaskOut
from app.db.write_db import async_write_session
from app.tasks import sync_task_created

logger = logging.getLogger(__name__)


async def create_task(payload: TaskCreateRequest):
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        title=payload.title,
        description=payload.description,
        is_completed=False,
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
