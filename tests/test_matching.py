"""Tests for Transparent Eligibility Matching Engine."""
import pytest
from app.db.models import JobListing
from app.matching.engine import MatchingEngine
from app.matching.schemas import EligibilityStatus, ScoringWeights


def test_deterministic_matching_eligible(test_db_session):
    """Candidate with required skills and experience is evaluated as ELIGIBLE."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
        candidate_exp_years=5.0,
        candidate_education=["B.S. in Computer Science"],
        job_title="Senior Python Backend Developer",
        job_description="Seeking a Python developer with 4 years of experience building FastAPI applications.",
        job_requirements=["Python", "FastAPI"],
    )
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.overall_score >= 70.0
    assert len(result.positive_matches) > 0
    assert len(result.missing_criteria) == 0


def test_deterministic_matching_ineligible_due_to_experience(test_db_session):
    """Candidate with 1 year experience applying to 8-year requirement is marked INELIGIBLE."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python"],
        candidate_exp_years=1.0,
        candidate_education=["B.S. in Computer Science"],
        job_title="Principal Architect",
        job_description="Mandatory 8+ years of experience required for leadership role.",
        job_requirements=["Python", "Kubernetes", "Architecture"],
    )
    assert result.status == EligibilityStatus.INELIGIBLE
    assert any("experience threshold" in m.lower() or "requires 8" in m.lower() for m in result.missing_criteria)


def test_deterministic_matching_needs_review(test_db_session):
    """Candidate with marginal qualifications is marked NEEDS_REVIEW."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python"],
        candidate_exp_years=3.0,
        candidate_education=[],
        job_title="Backend Developer",
        job_description="Looking for Python and Rust developer with degree preference.",
        job_requirements=["Rust", "Python"],
    )
    assert result.status == EligibilityStatus.NEEDS_REVIEW


def test_senior_role_lowered_priority_for_fresher(test_db_session):
    """Candidate with 0-1 years applying to Senior role is not marked STRONG_MATCH."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI", "Docker", "SQL"],
        candidate_exp_years=0.5,
        candidate_education=["B.Tech Computer Science"],
        job_title="Senior Python Architect",
        job_description="Senior Python developer with extensive system design expertise.",
        job_requirements=["Python", "FastAPI"],
    )
    # Even though skills matched, senior role must not be STRONG_MATCH for a fresher
    assert result.status in (EligibilityStatus.NEEDS_REVIEW, EligibilityStatus.INELIGIBLE)
    assert result.status != EligibilityStatus.STRONG_MATCH


def test_fresher_job_with_missing_preferred_skills_not_discarded(test_db_session):
    """Fresher job is not marked INELIGIBLE solely because optional/preferred skills are missing."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI", "SQL"],
        candidate_exp_years=0.0,
        candidate_education=["B.Tech"],
        job_title="Junior Python Intern / Trainee",
        job_description="Internship opening for fresh graduates with basic Python knowledge. Knowledge of AWS or Kubernetes is a plus.",
        job_requirements=["Python", "FastAPI"],
    )
    assert result.is_fresher_friendly is True
    assert result.status in (EligibilityStatus.STRONG_MATCH, EligibilityStatus.PARTIAL_MATCH)
    assert result.status != EligibilityStatus.INELIGIBLE


@pytest.mark.asyncio
async def test_ai_matching_engine_no_name_error_with_education(test_db_session, monkeypatch):
    """Bug 1 Regression Test: verify candidate_edu in AI prompt does not raise NameError."""
    from unittest.mock import AsyncMock
    from datetime import datetime, timezone
    from app.matching.schemas import MatchAssessment
    from app.ai.base import AIProvider

    # Create and add a test job
    job = JobListing(
        title="Junior Python Developer",
        company="TechCorp",
        location="Remote",
        description="Seeking an enthusiastic Junior Python Developer with knowledge of FastAPI and SQLite.",
        requirements='["Python", "FastAPI"]',
        application_url="https://techcorp.example.com/apply/1",
        source="Arbeitnow",
        fingerprint="techcorp_junior_python_123",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    # Mock AI provider to return structured assessment
    mock_ai = AsyncMock(spec=AIProvider)
    ai_result = MatchAssessment(
        overall_score=88.0,
        skills_score=90.0,
        experience_score=85.0,
        education_score=85.0,
        status=EligibilityStatus.STRONG_MATCH,
        rationale="Excellent candidate match with strong Python and FastAPI foundations.",
        positive_matches=["Python", "FastAPI"],
        missing_criteria=[],
        is_fresher_friendly=True,
    )
    mock_ai.generate_structured.return_value = ai_result

    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)

    # Verify AI provider was actually called and succeeded (not fallen back)
    assert mock_ai.generate_structured.called
    call_kwargs = mock_ai.generate_structured.call_args.kwargs
    # Check that education was successfully formatted in the prompt without NameError
    assert "B.S. Computer Science" in call_kwargs["prompt"]
    assert result.overall_score == 88.0
    assert result.status == EligibilityStatus.STRONG_MATCH




@pytest.mark.asyncio
async def test_ai_matching_engine_cache_hit(test_db_session, monkeypatch):
    """Phase 4 Test: verify matching engine uses match_fingerprint caching and skips redundant AI calls."""
    from unittest.mock import AsyncMock
    from datetime import datetime, timezone
    from app.matching.schemas import MatchAssessment
    from app.ai.base import AIProvider

    job = JobListing(
        title="Python Backend Developer",
        company="CacheCorp",
        location="Remote",
        description="We are looking for a Python Backend Developer skilled with FastAPI, SQLAlchemy, and Docker.",
        requirements='["Python", "FastAPI"]',
        application_url="https://cachecorp.example.com/apply/42",
        source="Arbeitnow",
        fingerprint="cachecorp_python_dev_42",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    ai_result = MatchAssessment(
        overall_score=94.0,
        skills_score=95.0,
        experience_score=90.0,
        education_score=90.0,
        status=EligibilityStatus.STRONG_MATCH,
        rationale="Top tier candidate match for Python backend engineering.",
        positive_matches=["Python", "FastAPI"],
        is_fresher_friendly=False,
    )
    mock_ai.generate_structured.return_value = ai_result
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)

    # First call: invokes AI
    match1 = await engine.evaluate_job(job.id)
    assert mock_ai.generate_structured.call_count == 1
    assert match1.overall_score == 94.0
    assert match1.is_fallback is False

    # Second call: cache hit, does NOT invoke AI again
    match2 = await engine.evaluate_job(job.id)
    assert mock_ai.generate_structured.call_count == 1
    assert match2.id == match1.id
    assert match2.overall_score == 94.0


@pytest.mark.asyncio
async def test_ai_matching_engine_fallback_on_ai_failure(test_db_session, monkeypatch):
    """Phase 4 Test: verify matching engine transparently falls back to rule-based engine when AI is unreachable."""
    from unittest.mock import AsyncMock
    from datetime import datetime, timezone
    from app.ai.base import AIProvider, AIProviderError

    job = JobListing(
        title="Junior Python Intern",
        company="FallBackCorp",
        location="Remote",
        description="Entry level internship for freshers who know basic Python and web concepts.",
        requirements='["Python"]',
        application_url="https://fallback.example.com/apply/99",
        source="Arbeitnow",
        fingerprint="fallback_junior_python_99",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.side_effect = AIProviderError("Connection timeout to Groq", provider="groq")
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)

    assert result.is_fallback is True
    assert "Rule-based fallback" in result.rationale
    assert result.overall_score > 0.0


@pytest.mark.asyncio
async def test_ai_matching_engine_low_information_warning(test_db_session, monkeypatch):
    """Phase 4 Test: verify short or placeholder descriptions generate a low-information warning."""
    from unittest.mock import AsyncMock
    from datetime import datetime, timezone
    from app.matching.schemas import MatchAssessment
    from app.ai.base import AIProvider

    job = JobListing(
        title="Software Engineer",
        company="BriefCorp",
        location="Remote",
        description="Vacancy: Software Engineer at BriefCorp. [Low-information]",
        requirements='[]',
        application_url="https://brief.example.com/apply/7",
        source="Ashby",
        fingerprint="briefcorp_sw_eng_7",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.return_value = MatchAssessment(
        overall_score=50.0,
        skills_score=50.0,
        experience_score=50.0,
        education_score=50.0,
        status=EligibilityStatus.NEEDS_REVIEW,
        rationale="Limited data available.",
    )
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)

    assert result.low_information_warning is not None
    assert "limited details" in result.low_information_warning
