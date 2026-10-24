"""Tests for Expanded Connectors (Arbeitnow, Greenhouse, Lever, Ashby, SmartRecruiters, LinkedIn, Internshala, Glassdoor)."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.jobs.connector_base import SourceCapability
from app.jobs.connectors.arbeitnow import ArbeitnowConnector
from app.jobs.connectors.ashby import AshbyConnector
from app.jobs.connectors.glassdoor import GlassdoorConnector
from app.jobs.connectors.greenhouse import GreenhouseConnector
from app.jobs.connectors.internshala import InternshalaConnector
from app.jobs.connectors.lever import LeverConnector
from app.jobs.connectors.jobicy import JobicyConnector
from app.jobs.connectors.linkedin import LinkedInConnector
from app.jobs.connectors.smartrecruiters import SmartRecruitersConnector
from app.jobs.registry import get_job_registry
from app.jobs.schemas import JobListingCreate


def test_registry_contains_all_expanded_sources():
    """Verify registry contains all 10 sources with valid capabilities."""
    registry = get_job_registry()
    sources = [
        "remoteok", "jobicy", "arbeitnow",
        "greenhouse", "lever", "ashby", "smartrecruiters",
        "linkedin", "internshala", "glassdoor"
    ]
    for s in sources:
        connector = registry.get(s)
        assert connector is not None, f"Source '{s}' missing from registry"
        caps = connector.capabilities
        assert isinstance(caps, SourceCapability)
        assert caps.source_name == s
        assert len(caps.compliance_policy) > 10


def test_compliance_matrix_distinguishes_automated_vs_assisted():
    """Verify that LinkedIn, Internshala, and Glassdoor declare bulk scraping disabled."""
    registry = get_job_registry()
    for s in ["linkedin", "internshala", "glassdoor"]:
        c = registry.get(s)
        assert c.capabilities.supports_job_fetching is False
        assert c.capabilities.supports_link_import is True
        assert c.capabilities.category == "assisted_import"

    # Automated APIs
    for s in ["remoteok", "jobicy", "arbeitnow", "greenhouse"]:
        c = registry.get(s)
        assert c.capabilities.supports_job_fetching is True


@pytest.mark.asyncio
async def test_arbeitnow_fetch_jobs_mock():
    """Verify Arbeitnow connector parses job vacancies from public API."""
    connector = ArbeitnowConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "slug": "senior-fastapi-engineer-123",
                "company_name": "Berlin Cloud Labs",
                "title": "Senior FastAPI Engineer",
                "description": "Building scalable backend services.",
                "remote": True,
                "url": "https://www.arbeitnow.com/view/senior-fastapi-engineer-123",
                "tags": ["Python", "FastAPI", "Docker"],
                "created_at": 1700000000,
            }
        ]
    }

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        jobs = await connector.fetch_jobs(limit=10)
        assert len(jobs) == 1
        j = jobs[0]
        assert j.title == "Senior FastAPI Engineer"
        assert j.company == "Berlin Cloud Labs"
        assert j.source == "arbeitnow"
        assert "FastAPI" in j.requirements


@pytest.mark.asyncio
async def test_greenhouse_fetch_jobs_mock():
    """Verify Greenhouse connector parses employer jobs from boards API."""
    connector = GreenhouseConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": 98765,
                "title": "Staff Backend Engineer",
                "location": {"name": "Remote, Global"},
                "content": "Looking for staff level Python backend engineer.",
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/98765",
            }
        ]
    }

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with patch.object(connector, "_get_target_boards", return_value=["gitlab"]):
            jobs = await connector.fetch_jobs(limit=10)
            assert len(jobs) == 1
            j = jobs[0]
            assert j.title == "Staff Backend Engineer"
            assert j.company == "Gitlab"
            assert j.source == "greenhouse"
            assert j.external_id == "98765"


@pytest.mark.asyncio
async def test_lever_fetch_jobs_mock():
    """Verify Lever connector parses employer postings."""
    connector = LeverConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": "lever-111",
            "text": "Platform Infrastructure Engineer",
            "categories": {"location": "London / Remote", "commitment": "Full-time", "team": "Platform"},
            "descriptionPlain": "Kubernetes and Python platform work.",
            "hostedUrl": "https://jobs.lever.co/deliveroo/lever-111",
        }
    ]

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with patch.object(connector, "_get_target_companies", return_value=["deliveroo"]):
            jobs = await connector.fetch_jobs(limit=10)
            assert len(jobs) == 1
            j = jobs[0]
            assert j.title == "Platform Infrastructure Engineer"
            assert j.company == "Deliveroo"
            assert j.source == "lever"


@pytest.mark.asyncio
async def test_ashby_fetch_jobs_mock():
    """Verify Ashby connector parses employer job board postings."""
    connector = AshbyConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": "ashby-222",
                "title": "Machine Learning Engineer",
                "department": "AI Research",
                "location": "San Francisco, CA",
                "jobUrl": "https://jobs.ashbyhq.com/org/ashby-222",
            }
        ]
    }

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with patch.object(connector, "_get_target_organizations", return_value=["openai"]):
            jobs = await connector.fetch_jobs(limit=10)
            assert len(jobs) == 1
            assert jobs[0].title == "Machine Learning Engineer"
            assert jobs[0].source == "ashby"


@pytest.mark.asyncio
async def test_smartrecruiters_fetch_jobs_mock():
    """Verify SmartRecruiters connector parses employer postings."""
    connector = SmartRecruitersConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [
            {
                "id": "sr-333",
                "name": "Cloud DevOps Engineer",
                "location": {"city": "New York", "country": "US"},
            }
        ]
    }

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        with patch.object(connector, "_get_target_companies", return_value=["visa"]):
            jobs = await connector.fetch_jobs(limit=10)
            assert len(jobs) == 1
            assert jobs[0].title == "Cloud DevOps Engineer"
            assert jobs[0].source == "smartrecruiters"


@pytest.mark.asyncio
async def test_jobicy_fetch_jobs_with_list_fields_mock():
    """Verify Jobicy connector parses jobs when jobType, jobGeo, or jobLevel are lists."""
    connector = JobicyConnector()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": "jobicy-999",
                "jobTitle": "Junior AI Engineer",
                "companyName": "DeepTech Labs",
                "jobType": ["Full-Time"],
                "jobGeo": ["Remote", "Worldwide"],
                "jobLevel": ["Entry-Level"],
                "jobIndustry": ["Artificial Intelligence", "Python"],
                "url": "https://jobicy.com/jobs/junior-ai-engineer",
                "pubDate": "2026-10-24T10:00:00Z",
                "annualSalaryMin": "60000",
                "annualSalaryMax": "90000",
                "salaryCurrency": "USD",
                "jobDescription": "<p>Exciting junior AI position developing autonomous agents.</p>",
            }
        ]
    }

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        jobs = await connector.fetch_jobs(limit=10)
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Junior AI Engineer"
        assert job.company == "DeepTech Labs"
        assert job.employment_type == "Full-Time"
        assert job.location == "Remote, Worldwide"
        assert job.experience_level == "Entry-Level"
        assert "Artificial Intelligence" in job.requirements
        assert job.source == "jobicy"


def test_job_listing_schema_normalizes_list_fields():
    """Verify JobListingCreate normalizes list inputs for employment_type, location, and experience_level."""
    job = JobListingCreate(
        title="Python Backend Developer",
        company="FastAPI Corp",
        location=["Remote", "India"],
        employment_type=["Full-Time", "Contract"],
        experience_level=["Junior", "Entry-level"],
        description="FastAPI, async SQLite, and agent development.",
        application_url="https://example.com/apply/123",
        source="test_source",
    )
    assert job.location == "Remote, India"
    assert job.employment_type == "Full-Time, Contract"
    assert job.experience_level == "Junior, Entry-level"

