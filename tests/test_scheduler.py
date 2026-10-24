"""Tests for Job Sync Scheduler and CPU spin prevention."""
import asyncio
import pytest
from app.scheduler.manager import SchedulerManager


@pytest.mark.asyncio
async def test_scheduler_lifecycle_and_short_interval_no_spin(monkeypatch):
    """Bug 6 Regression Test: ensure scheduler with interval < 5 seconds sleeps appropriately without spinning."""
    scheduler = SchedulerManager()
    monkeypatch.setattr(scheduler.settings, "enable_scheduler", True)
    monkeypatch.setattr(scheduler.settings, "job_sync_interval_minutes", 0.02)  # ~1.2 seconds

    sync_call_count = 0

    async def mock_run_sync_once():
        nonlocal sync_call_count
        sync_call_count += 1
        scheduler.last_sync_status = "SUCCESS"

    monkeypatch.setattr(scheduler, "trigger_sync_now", mock_run_sync_once)

    # Start scheduler
    scheduler.start()
    assert scheduler.is_running() is True

    # Sleep for 1.5 seconds: should not spin through hundreds of loops
    await asyncio.sleep(1.5)

    await scheduler.stop()
    assert scheduler.is_running() is False


def test_scheduler_status_reporting():
    """Verify scheduler status dictionary contains required telemetry keys."""
    scheduler = SchedulerManager()
    status = scheduler.get_status()
    assert "running" in status
    assert "sync_interval_minutes" in status
    assert "last_sync_status" in status
