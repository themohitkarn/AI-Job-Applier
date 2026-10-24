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
