"""Tests for FastAPI HTTP Endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from app.db.session import get_db


@pytest.mark.asyncio
async def test_health_endpoint(test_db_session):
    """Verify system readiness endpoint returns HTTP 200."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["database"] == "healthy"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_config_endpoint_sanitization():
    """Verify /config endpoint does not expose sensitive secret keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "groq_configured" in data
        assert "groq_api_key" not in data
        assert "secret_key" not in data


@pytest.mark.asyncio
async def test_profile_endpoints(test_db_session):
    """Verify profile retrieval and update endpoints."""
    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Get profile
            resp = await client.get("/api/v1/profile")
            assert resp.status_code == 200
            prof_data = resp.json()
            assert prof_data["full_name"] == "Alex Engineer"

            # Update profile
            update_payload = {
                "headline": "Lead Python Architect",
                "skills": ["Python", "FastAPI", "Kubernetes", "PyTest"],
            }
            resp_update = await client.put("/api/v1/profile", json=update_payload)
            assert resp_update.status_code == 200
            updated_data = resp_update.json()
            assert updated_data["headline"] == "Lead Python Architect"
            assert "Kubernetes" in updated_data["skills"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scheduler_status_endpoint():
    """Verify scheduler status endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/scheduler/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "running" in data


@pytest.mark.asyncio
async def test_dashboard_endpoint():
    """Verify web dashboard HTML serves correctly with security & fresher features."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        html = resp.text
        assert "ai-warning-banner" in html
        assert "job-sort-select" in html
        assert "work-mode-select" in html
        assert "fresher-only-checkbox" in html
        assert "escapeHtml" in html


@pytest.mark.asyncio
async def test_job_listing_endpoint_with_sorting_and_clean_descriptions(test_db_session):
    """Verify jobs endpoint supports sorting and returns clean descriptions."""
    from app.jobs.schemas import JobListingCreate
    from app.jobs.service import JobService

    service = JobService(test_db_session)
    # Insert a job with HTML in description
    dirty_html = '<div class="gmail_default">Looking for an <b>AI Intern</b> with Python skills.</div>'
    await service.save_or_update_job(JobListingCreate(
        title="AI Engineer Intern",
        company="TechCorp AI",
        location="Remote",
        description=dirty_html,
        application_url="https://techcorp.ai/careers/intern-1",
        source="arbeitnow",
    ))

    app.dependency_overrides[get_db] = lambda: test_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs?sort_by=fresher_first")
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) >= 1
            # Check description is cleaned
            job_item = next(j for j in data["items"] if j["company"] == "TechCorp AI")
            assert '<div class="gmail_default">' not in job_item["description"]
            assert "Looking for an AI Intern with Python skills." in job_item["description"]
            assert job_item["application_url"] == "https://techcorp.ai/careers/intern-1"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_health_endpoint_diagnostics():
    """Verify /api/v1/health/ai returns clear status and does not leak keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/ai")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "provider" in data
        assert "gsk_" not in str(data)  # Never expose Groq keys in response!
