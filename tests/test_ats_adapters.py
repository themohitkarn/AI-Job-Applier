"""Tests for ATS Form Adapters (Greenhouse, Lever, and Dynamic Adapter Selection)."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.automation.adapters.generic import GenericJobAdapter
from app.automation.adapters.greenhouse import GreenhouseAdapter
from app.automation.adapters.lever import LeverAdapter
from app.automation.browser import BrowserAutomationService


def test_adapter_can_handle_matching():
    """Verify ATS adapters recognize their target hostnames."""
    gh = GreenhouseAdapter()
    assert gh.can_handle("https://boards.greenhouse.io/gitlab/jobs/123") is True
    assert gh.can_handle("https://jobs.lever.co/deliveroo/456") is False

    lever = LeverAdapter()
    assert lever.can_handle("https://jobs.lever.co/deliveroo/456") is True
    assert lever.can_handle("https://boards.greenhouse.io/gitlab/jobs/123") is False

    generic = GenericJobAdapter()
    assert generic.can_handle("https://random-company.com/apply") is True


@pytest.mark.asyncio
async def test_greenhouse_adapter_form_filling():
    """Verify Greenhouse adapter populates first_name, last_name, email, phone."""
    adapter = GreenhouseAdapter()

    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.is_visible = AsyncMock(return_value=True)
    mock_locator.fill = AsyncMock()
    mock_locator.set_input_files = AsyncMock()

    mock_page.locator.return_value.first = mock_locator

    profile = {
        "full_name": "Elena Rostova",
        "email": "elena@example.com",
        "phone": "+1-555-0199",
    }

    filled = await adapter.fill_form(page=mock_page, profile_data=profile)
    assert filled["first_name"] == "Elena"
    assert filled["last_name"] == "Rostova"
    assert filled["email"] == "elena@example.com"
    assert filled["phone"] == "+1-555-0199"


@pytest.mark.asyncio
async def test_lever_adapter_form_filling():
    """Verify Lever adapter populates name, email, phone."""
    adapter = LeverAdapter()

    mock_page = MagicMock()
    mock_locator = MagicMock()
    mock_locator.is_visible = AsyncMock(return_value=True)
    mock_locator.fill = AsyncMock()

    mock_page.locator.return_value.first = mock_locator

    profile = {
        "full_name": "Marcus Vance",
        "email": "marcus@example.com",
        "phone": "555-0144",
    }

    filled = await adapter.fill_form(page=mock_page, profile_data=profile)
    assert filled["name"] == "Marcus Vance"
    assert filled["email"] == "marcus@example.com"
    assert filled["phone"] == "555-0144"


def test_browser_automation_service_adapter_selection(test_db_session):
    """Verify BrowserAutomationService dynamically selects specialized adapter."""
    service = BrowserAutomationService(test_db_session)

    gh_adapter = service._select_adapter("https://boards.greenhouse.io/stripe/jobs/1")
    assert isinstance(gh_adapter, GreenhouseAdapter)

    lever_adapter = service._select_adapter("https://jobs.lever.co/spotify/2")
    assert isinstance(lever_adapter, LeverAdapter)

    gen_adapter = service._select_adapter("https://careers.company.org/apply")
    assert isinstance(gen_adapter, GenericJobAdapter)
