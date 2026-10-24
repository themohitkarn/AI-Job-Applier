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
