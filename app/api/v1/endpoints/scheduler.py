"""Background scheduler control and status endpoints."""
from typing import Any, Dict
from fastapi import APIRouter
from app.scheduler.manager import get_scheduler

router = APIRouter(prefix="/scheduler", tags=["Background Scheduler"])


@router.get("/status", summary="Get background scheduler status and execution history")
async def get_scheduler_status() -> Dict[str, Any]:
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.post("/sync", summary="Trigger manual asynchronous background synchronization")
async def trigger_sync() -> Dict[str, Any]:
    scheduler = get_scheduler()
    result = await scheduler.trigger_sync_now()
    return result
