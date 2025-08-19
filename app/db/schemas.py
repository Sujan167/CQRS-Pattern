from datetime import datetime
from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""


class TaskOut(BaseModel):
    id: str
    title: str
    description: str
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Enables ORM conversion


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    is_completed: bool | None = None
