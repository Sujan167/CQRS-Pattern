import logging
from fastapi import FastAPI, HTTPException
from fastapi.params import Body
from app.db.schemas import TaskCreateRequest, TaskOut
from app.commands.create_task import create_task
from app.commands.update_task import update_task
from app.commands.delete_task import delete_task
from app.queries.get_task import get_task
from app.queries.get_task_by_id import get_task_by_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/tasks", response_model=TaskOut)
async def create_task_endpoint(payload: TaskCreateRequest):
    logger.info(f"Creating task with title: {payload.title}")
    return await create_task(payload)


@app.get("/tasks")
async def get_task_endpoint():
    tasks = await get_task()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task_by_id_endpoint(task_id: str):
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task_endpoint(
    task_id: str,
    title: str | None = Body(default=None),
    description: str | None = Body(default=None),
    is_completed: bool | None = Body(default=None),
):
    updated = await update_task(task_id, title=title, description=description, is_completed=is_completed)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    ok = await delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "id": task_id}
