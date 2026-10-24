"""Tests for Job Normalization, Deduplication, and Service Persistence."""
import pytest
from app.jobs.dedup import compute_job_fingerprint, normalize_job_url
from app.jobs.schemas import JobListingCreate, JobListingFilter
from app.jobs.service import JobService


def test_normalize_job_url():
    """Verify marketing tracking query parameters are cleanly stripped."""
    raw = "https://jobs.example.com/apply/123/?utm_source=linkedin&utm_campaign=winter&ref=newsletter"
    expected = "https://jobs.example.com/apply/123"
    assert normalize_job_url(raw) == expected


def test_job_fingerprint_deterministic_and_invariant():
    """Verify equivalent job representations compute identical fingerprints."""
    fp1 = compute_job_fingerprint(
        company="Acme Technologies Inc.",
        title="Senior Python Engineer",
        url="https://acme.com/jobs/456?utm_source=google",
    )
    fp2 = compute_job_fingerprint(
        company="Acme Technologies, LLC",
        title="Senior Python Engineer",
        url="https://acme.com/jobs/456",
    )
    assert fp1 == fp2


@pytest.mark.asyncio
async def test_job_service_deduplication(test_db_session):
    """Verify inserting duplicate jobs does not create duplicate database rows."""
    service = JobService(test_db_session)

    async def mock_fetch(keywords=None, location=None, limit=50):
        return [
            JobListingCreate(
                title="Python Backend Developer",
                company="Innovate Labs",
                location="Remote",
                description="FastAPI role",
                requirements=["Python", "FastAPI"],
                application_url="https://innovate.io/apply?utm_medium=email",
                source="mock_board",
                external_id="job-999",
            )
        ]

    mock_connector = type("MockConnector", (), {
        "name": "mock_board",
        "fetch_jobs": lambda self, keywords=None, location=None, limit=50: mock_fetch(keywords, location, limit)
    })()

    service.registry.register(mock_connector)
    try:
        rec1 = await service.sync_connector("mock_board")
        assert rec1.jobs_added == 1

        # Second sync with identical external job
        rec2 = await service.sync_connector("mock_board")
        assert rec2.jobs_added == 0  # Deduplicated

        # Search jobs
        items, total = await service.search_jobs(JobListingFilter(query="Innovate"))
        assert total == 1
        assert items[0].company == "Innovate Labs"
    finally:
        service.registry.unregister("mock_board")
