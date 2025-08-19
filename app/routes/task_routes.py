import logging
from fastapi import APIRouter, HTTPException
from fastapi.params import Body
from app.db.schemas import TaskCreateRequest, TaskOut
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskOut)
async def create_task_endpoint(payload: TaskCreateRequest):
    """Create a new task"""
    return await TaskService.create_task(payload)


@router.get("/")
async def get_task_endpoint():
    """Get all tasks"""
    tasks = await TaskService.get_all_tasks()
    return tasks


@router.get("/{task_id}", response_model=TaskOut)
async def get_task_by_id_endpoint(task_id: str):
    """Get a specific task by ID"""
    task = await TaskService.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task_endpoint(
    task_id: str,
    title: str | None = Body(default=None),
    description: str | None = Body(default=None),
    is_completed: bool | None = Body(default=None),
):
    """Update a specific task by ID"""
    updated = await TaskService.update_task(
        task_id, 
        title=title, 
        description=description, 
        is_completed=is_completed
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{task_id}")
async def delete_task_endpoint(task_id: str):
    """Delete a specific task by ID"""
    ok = await TaskService.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "id": task_id}
