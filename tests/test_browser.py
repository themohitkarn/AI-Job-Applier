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
