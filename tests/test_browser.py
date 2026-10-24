"""Tests for Browser Automation and User Approval Workflow."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.automation.adapters.generic import GenericJobAdapter
from app.automation.schemas import ApplicationStatus, BrowserActionRequest


@pytest.mark.asyncio
async def test_generic_adapter_field_filling():
    """Verify generic adapter locates inputs and maps candidate fields."""
    adapter = GenericJobAdapter()

    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.is_visible = AsyncMock(return_value=True)
    mock_locator.fill = AsyncMock()
    mock_locator.set_input_files = AsyncMock()

    mock_page.locator.return_value.first = mock_locator

    profile = {
        "full_name": "Jordan Developer",
        "email": "jordan@example.com",
        "phone": "555-0199",
    }

    filled = await adapter.fill_form(page=mock_page, profile_data=profile)
    assert filled["full_name"] == "Jordan Developer"
    assert filled["email"] == "jordan@example.com"
    assert filled["phone"] == "555-0199"


@pytest.mark.asyncio
async def test_submission_confirmation_detection():
    """Verify adapter recognizes legitimate submission confirmations."""
    adapter = GenericJobAdapter()

    # Confirmed page
    mock_page_success = MagicMock()
    mock_page_success.content = AsyncMock(return_value="<html><body><h1>Thank You For Applying!</h1><p>We received your application.</p></body></html>")
    mock_page_success.locator.return_value.all_inner_texts = AsyncMock(return_value=["Thank You For Applying!"])

    is_confirmed, ref = await adapter.check_submission_confirmation(mock_page_success)
    assert is_confirmed is True

    # Incomplete page
    mock_page_incomplete = MagicMock()
    mock_page_incomplete.content = AsyncMock(return_value="<html><body><form><button>Submit</button></form></body></html>")
    mock_page_incomplete.locator.return_value.all_inner_texts = AsyncMock(return_value=[])

    is_confirmed2, ref2 = await adapter.check_submission_confirmation(mock_page_incomplete)
    assert is_confirmed2 is False



@pytest.mark.asyncio
async def test_browser_launch_failure_handled_cleanly(test_db_session, monkeypatch):
    """Bug 3 Regression Test: verify browser launch failure returns FAILED response without crashing with UnboundLocalError."""
    from datetime import datetime, timezone
    from app.automation.browser import BrowserAutomationService
    from app.automation.schemas import BrowserActionRequest
    from app.db.models import JobListing

    job = JobListing(
        title="Test Role",
        company="Test Co",
        location="Remote",
        description="Role description",
        application_url="https://example.com/apply/123",
        source="arbeitnow",
        fingerprint="test_launch_failure_fp_123",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    # Mock playwright launch to raise an error (e.g. missing binary)
    class FakePlaywrightContext:
        async def __aenter__(self):
            class FakeChromium:
                async def launch(self, *args, **kwargs):
                    raise RuntimeError("Chromium binary missing in headless environment")
            class FakeP:
                chromium = FakeChromium()
            return FakeP()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.automation.browser.async_playwright", lambda: FakePlaywrightContext())

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=True)
    resp = await service.execute_application_flow(req)

    assert resp.status == ApplicationStatus.FAILED
    assert "Chromium binary missing" in (resp.error_message or "")
    assert not resp.requires_user_approval



@pytest.mark.asyncio
async def test_browser_automation_ineligible_role_safety_block(test_db_session):
    """Phase 5 Test: verify candidate evaluated as INELIGIBLE cannot be auto-applied without confirmation."""
    from datetime import datetime, timezone
    from app.automation.browser import BrowserAutomationService
    from app.automation.schemas import BrowserActionRequest
    from app.db.models import JobListing, JobMatch, UserProfile
    from sqlalchemy import select

    stmt_user = select(UserProfile).order_by(UserProfile.id.asc()).limit(1)
    user = (await test_db_session.execute(stmt_user)).scalar_one()

    job = JobListing(
        title="VP of Engineering",
        company="BlockCorp",
        location="Remote",
        description="Requires 15+ years of engineering leadership.",
        application_url="https://blockcorp.example.com/apply/1",
        source="Arbeitnow",
        fingerprint="blockcorp_vp_eng_1",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    # Record INELIGIBLE match
    match_rec = JobMatch(
        job_id=job.id,
        user_id=user.id,
        overall_score=15.0,
        skills_score=20.0,
        experience_score=0.0,
        education_score=50.0,
        status="INELIGIBLE",
        rationale="Candidate experience does not satisfy minimum 15 years leadership threshold.",
    )
    test_db_session.add(match_rec)
    await test_db_session.commit()

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=True, user_confirmed_submission=False)

    with pytest.raises(ValueError) as exc_info:
        await service.execute_application_flow(req)

    assert "Pre-Application Safety Check" in str(exc_info.value)
    assert "INELIGIBLE" in str(exc_info.value)


@pytest.mark.asyncio
async def test_browser_automation_detects_captcha_and_sets_manual_action_required(test_db_session, monkeypatch):
    """Phase 5 Test: verify CAPTCHA / bot challenge flags application as MANUAL_ACTION_REQUIRED."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock
    from app.automation.browser import BrowserAutomationService
    from app.automation.schemas import ApplicationStatus, BrowserActionRequest
    from app.db.models import JobListing

    job = JobListing(
        title="Staff Engineer",
        company="CaptchaCorp",
        location="Remote",
        description="Software role behind Cloudflare protection.",
        application_url="https://captchacorp.example.com/apply/2",
        source="Arbeitnow",
        fingerprint="captchacorp_staff_2",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    class FakePlaywrightContext:
        async def __aenter__(self):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.screenshot = AsyncMock()
            # Simulate bot challenge text
            mock_page.content = AsyncMock(return_value="<html><body><p>Please verify you are a human to continue</p></body></html>")
            mock_locator = MagicMock()
            mock_locator.first.is_visible = AsyncMock(return_value=False)
            mock_page.locator.return_value = mock_locator

            mock_ctx = MagicMock()
            mock_ctx.new_page = AsyncMock(return_value=mock_page)

            mock_browser = MagicMock()
            mock_browser.new_context = AsyncMock(return_value=mock_ctx)
            mock_browser.close = AsyncMock()

            class FakeChromium:
                async def launch(self, *args, **kwargs):
                    return mock_browser

            class FakeP:
                chromium = FakeChromium()
            return FakeP()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.automation.browser.async_playwright", lambda: FakePlaywrightContext())

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=True)
    resp = await service.execute_application_flow(req)

    assert resp.status == ApplicationStatus.MANUAL_ACTION_REQUIRED
    assert "Bot protection" in resp.message or "challenge detected" in resp.message
    assert not resp.requires_user_approval
