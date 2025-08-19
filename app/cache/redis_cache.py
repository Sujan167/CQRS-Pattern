import redis  # sync client for worker
import os
import json
import logging
from typing import List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Use asyncio client for API runtime, and sync client for Celery worker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

try:
    # redis>=4 provides asyncio submodule
    from redis import asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - fallback if package lacks asyncio
    aioredis = None  # type: ignore


def _default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# Keys
def _task_key(task_id: str) -> str:
    return f"task:{task_id}"


TASK_INDEX_KEY = "tasks:index"  # set of task ids


# ---------- Async API (FastAPI) ----------
_async_client = aioredis.from_url(
    REDIS_URL, decode_responses=True) if aioredis else None


async def cache_add_task_async(task: dict) -> None:
    if not _async_client:
        return
    task_id = task["id"]
    await _async_client.set(_task_key(task_id), json.dumps(task, default=_default_serializer), ex=CACHE_TTL_SECONDS)
    await _async_client.sadd(TASK_INDEX_KEY, task_id)


async def cache_remove_task_async(task_id: str) -> None:
    if not _async_client:
        return
    await _async_client.delete(_task_key(task_id))
    await _async_client.srem(TASK_INDEX_KEY, task_id)


async def cache_get_all_ids_async() -> List[str]:
    if not _async_client:
        return []
    ids = await _async_client.smembers(TASK_INDEX_KEY)
    return list(ids) if ids else []


async def cache_get_tasks_by_ids_async(task_ids: List[str]) -> Tuple[List[dict], List[str]]:
    if not _async_client or not task_ids:
        return [], task_ids
    pipe = _async_client.pipeline()
    for task_id in task_ids:
        pipe.get(_task_key(task_id))
    raw_values = await pipe.execute()
    tasks: List[dict] = []
    missing: List[str] = []
    for task_id, raw in zip(task_ids, raw_values):
        if raw:
            tasks.append(json.loads(raw))
        else:
            missing.append(task_id)
    return tasks, missing


async def cache_set_index_async(task_ids: List[str]) -> None:
    if not _async_client:
        return
    await _async_client.delete(TASK_INDEX_KEY)
    if task_ids:
        await _async_client.sadd(TASK_INDEX_KEY, *task_ids)


# ---------- Sync API (Celery worker) ----------
_sync_client = redis.from_url(REDIS_URL, decode_responses=True)


def cache_add_task_sync(task: dict) -> None:
    task_id = task["id"]
    _sync_client.set(_task_key(task_id), json.dumps(
        task, default=_default_serializer), ex=CACHE_TTL_SECONDS)
    _sync_client.sadd(TASK_INDEX_KEY, task_id)


def cache_remove_task_sync(task_id: str) -> None:
    _sync_client.delete(_task_key(task_id))
    _sync_client.srem(TASK_INDEX_KEY, task_id)


def cache_set_index_sync(task_ids: List[str]) -> None:
    _sync_client.delete(TASK_INDEX_KEY)
    if task_ids:
        _sync_client.sadd(TASK_INDEX_KEY, *task_ids)
