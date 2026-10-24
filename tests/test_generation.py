"""Tests for Application Content Generation, Caching, and Draft Approvals."""
from unittest.mock import AsyncMock, patch
import pytest
from app.db.models import JobListing
from app.generation.cache import compute_generation_fingerprint
from app.generation.schemas import ApproveDraftRequest, DraftType, GenerateContentRequest
from app.generation.service import ContentService


def test_generation_fingerprint_invalidation():
    """Different prompt versions or instructions produce distinct fingerprints."""
    fp1 = compute_generation_fingerprint(job_id=1, profile_hash="hash_a", draft_type="cover_letter", custom_instructions="Focus on API design")
    fp2 = compute_generation_fingerprint(job_id=1, profile_hash="hash_a", draft_type="cover_letter", custom_instructions="Focus on Machine Learning")
    assert fp1 != fp2


@pytest.mark.asyncio
async def test_content_generation_and_caching(test_db_session):
    """Generated content is persisted and cached on subsequent queries."""
    # Insert dummy job
    job = JobListing(
        source="manual",
        title="FastAPI Developer",
        company="Startup Co",
        description="FastAPI engineer position",
        application_url="https://example.com/apply",
        fingerprint="dummy_fp_12345",
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    service = ContentService(test_db_session)

    with patch("app.generation.service.get_ai_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "Subject: Application for FastAPI Developer\n\nDear Hiring Team,\nI am writing to express my strong interest in the FastAPI role..."
        mock_get_provider.return_value = mock_provider

        req = GenerateContentRequest(job_id=job.id, draft_type=DraftType.COVER_LETTER)
        resp1 = await service.generate_content(req)
        assert resp1.cached is False
        assert resp1.job_id == job.id
        assert "FastAPI" in resp1.content

        # Second call should return cached draft without invoking AI
        resp2 = await service.generate_content(req)
        assert resp2.cached is True
        assert resp2.id == resp1.id


@pytest.mark.asyncio
async def test_draft_approval(test_db_session):
    """User can approve and edit drafts."""
    job = JobListing(
        source="manual",
        title="Python Engineer",
        company="Global Corp",
        description="Python role",
        application_url="https://example.com/apply2",
        fingerprint="dummy_fp_67890",
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    service = ContentService(test_db_session)
    with patch("app.generation.service.get_ai_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "Subject: Draft\n\nOriginal content"
        mock_get_provider.return_value = mock_provider

        draft_resp = await service.generate_content(GenerateContentRequest(job_id=job.id))

    # Approve draft with user edit
    approved = await service.approve_draft(
        draft_resp.id,
        ApproveDraftRequest(is_approved=True, edited_content="Polished by user")
    )
    assert approved.is_approved is True
    assert approved.content == "Polished by user"
