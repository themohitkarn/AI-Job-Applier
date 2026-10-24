"""Tests for Sources Capability API and Job Import Endpoints."""
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from app.db.session import get_db
from app.jobs.schemas import JobListingCreate


@pytest.mark.asyncio
async def test_sources_capability_endpoint(test_db_session):
    """Verify /api/v1/jobs/sources returns capability matrix for all sources."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs/sources")
            assert resp.status_code == 200
            sources = resp.json()
            assert len(sources) >= 10

            source_names = [s["source_name"] for s in sources]
            assert "remoteok" in source_names
            assert "jobicy" in source_names
            assert "arbeitnow" in source_names
            assert "greenhouse" in source_names
            assert "lever" in source_names
            assert "ashby" in source_names
            assert "smartrecruiters" in source_names
            assert "linkedin" in source_names
            assert "internshala" in source_names
            assert "glassdoor" in source_names

            # Verify LinkedIn capability flags
            linkedin_caps = next(s for s in sources if s["source_name"] == "linkedin")
            assert linkedin_caps["supports_job_fetching"] is False
            assert linkedin_caps["supports_link_import"] is True
            assert linkedin_caps["category"] == "assisted_import"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_import_job_endpoint(test_db_session):
    """Verify /api/v1/jobs/import endpoint parses URL and persists job record."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        mock_parsed = JobListingCreate(
            title="Imported Fullstack Engineer",
            company="Acme Corp",
            location="Remote",
            description="Fullstack role description.",
            application_url="https://jobs.example.com/posting/123",
            source="linkedin",
        )

        with patch("app.jobs.service.fetch_and_parse_job_url", AsyncMock(return_value=mock_parsed)):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                payload = {
                    "url": "https://www.linkedin.com/jobs/view/99999999",
                }
                resp = await client.post("/api/v1/jobs/import", json=payload)
                assert resp.status_code == 201
                data = resp.json()
                assert data["title"] == "Imported Fullstack Engineer"
                assert data["company"] == "Acme Corp"
                assert data["is_new"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manual_job_endpoint(test_db_session):
    """Verify /api/v1/jobs/manual creates a custom job vacancy."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "title": "Manual Python Developer",
                "company": "Direct Employer LLC",
                "location": "New York, NY",
                "description": "Direct hire Python developer.",
                "application_url": "https://employer.com/apply/python",
                "source": "manual",
            }
            resp = await client.post("/api/v1/jobs/manual", json=payload)
            assert resp.status_code == 201
            data = resp.json()
            assert data["title"] == "Manual Python Developer"
            assert data["company"] == "Direct Employer LLC"
            assert data["is_new"] is True
    finally:
        app.dependency_overrides.clear()
