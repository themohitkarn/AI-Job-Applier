"""Background asynchronous task scheduler."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.jobs.service import JobService

logger = get_logger("scheduler")


class SchedulerManager:
    """Manages periodic job synchronization and cache maintenance tasks."""

    def __init__(self):
        self.settings = get_settings()
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self.last_sync_time: Optional[datetime] = None
        self.last_cleanup_time: Optional[datetime] = None
        self.last_sync_status: str = "IDLE"

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start asynchronous periodic worker loops."""
        if not self.settings.enable_scheduler:
            logger.info("Scheduler is disabled by configuration (ENABLE_SCHEDULER=false).")
            return
        if self._running:
            return

        self._running = True
        self._sync_task = asyncio.create_task(self._periodic_sync_loop())
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_loop())
        logger.info("Scheduler started successfully.")

    async def stop(self) -> None:
        """Gracefully terminate background scheduler tasks."""
        if not self._running:
            return
        self._running = False
        for task in [self._sync_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Scheduler stopped.")

    async def _periodic_sync_loop(self) -> None:
        """Periodic loop to discover new jobs from enabled sources."""
        interval_seconds = self.settings.job_sync_interval_minutes * 60
        while self._running:
            try:
                logger.info("Periodic job sync triggered.")
                self.last_sync_status = "RUNNING"
                async with AsyncSessionLocal() as session:
                    service = JobService(session)
                    await service.sync_all_enabled_sources()
                self.last_sync_time = datetime.now(timezone.utc)
                self.last_sync_status = "SUCCESS"
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_sync_status = "FAILED"
                logger.error(f"Error in periodic job sync: {e}")

            # Sleep in intervals to check _running flag
            sleep_chunk = min(5.0, max(0.5, float(interval_seconds)))
            for _ in range(max(1, int(interval_seconds / sleep_chunk))):
                if not self._running:
                    break
                await asyncio.sleep(sleep_chunk)

    async def _periodic_cleanup_loop(self) -> None:
        """Periodic loop to clear expired cache files."""
        interval_seconds = self.settings.scheduler_cache_cleanup_hours * 3600
        while self._running:
            try:
                logger.info("Cache cleanup triggered.")
                cache_dir = self.settings.cache_dir
                if cache_dir.exists():
                    now = datetime.now(timezone.utc).timestamp()
                    for f in cache_dir.glob("*.txt"):
                        # If older than cleanup threshold
                        if now - f.stat().st_mtime > interval_seconds:
                            try:
                                f.unlink()
                            except Exception:
                                pass
                self.last_cleanup_time = datetime.now(timezone.utc)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cache cleanup: {e}")

            for _ in range(int(interval_seconds / 10)):
                if not self._running:
                    break
                await asyncio.sleep(10)

    async def trigger_sync_now(self) -> Dict[str, Any]:
        """Trigger an immediate out-of-band synchronization."""
        self.last_sync_status = "RUNNING"
        try:
            async with AsyncSessionLocal() as session:
                service = JobService(session)
                records = await service.sync_all_enabled_sources()
            self.last_sync_time = datetime.now(timezone.utc)
            self.last_sync_status = "SUCCESS"
            return {
                "status": "SUCCESS",
                "sources_synced": len(records),
                "timestamp": self.last_sync_time.isoformat(),
            }
        except Exception as e:
            self.last_sync_status = "FAILED"
            return {
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.settings.enable_scheduler,
            "running": self._running,
            "last_sync_status": self.last_sync_status,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "last_cleanup_time": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            "sync_interval_minutes": self.settings.job_sync_interval_minutes,
        }


# Singleton scheduler instance
scheduler = SchedulerManager()


def get_scheduler() -> SchedulerManager:
    return scheduler
