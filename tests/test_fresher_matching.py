"""Comprehensive tests for Fresher-Friendly Job Search, Keyword Groups, Synonyms, and Eligibility Categories."""
import json
import pytest
from app.core.config import Settings
from app.core.keywords import (
    DEFAULT_KEYWORD_GROUPS,
    TECHNICAL_SYNONYMS,
    detect_fresher_friendly,
    detect_work_modes,
    discover_title_variations,
    match_skills_with_synonyms,
    split_mandatory_vs_preferred,
)
from app.jobs.schemas import JobListingCreate, JobListingFilter
from app.jobs.service import JobService
from app.matching.engine import MatchingEngine
from app.matching.schemas import EligibilityStatus


def test_keyword_groups_taxonomy():
    """Verify all 5 required domains are present with comprehensive job titles and skills."""
    assert "ai_ml" in DEFAULT_KEYWORD_GROUPS
    assert "python_backend" in DEFAULT_KEYWORD_GROUPS
    assert "web_fullstack" in DEFAULT_KEYWORD_GROUPS
    assert "software_engineering" in DEFAULT_KEYWORD_GROUPS
    assert "database_data" in DEFAULT_KEYWORD_GROUPS

    ai_kws = DEFAULT_KEYWORD_GROUPS["ai_ml"]
    assert any("AI Engineer" in k for k in ai_kws)
    assert any("GenAI" in k or "Generative AI" in k for k in ai_kws)
    assert any("Agentic AI" in k or "Multi-Agent" in k for k in ai_kws)
    assert any("RAG" in k for k in ai_kws)
    assert any("Prompt Engineering" in k for k in ai_kws)
    assert any("ML Intern" in k for k in ai_kws)

    backend_kws = DEFAULT_KEYWORD_GROUPS["python_backend"]
    assert any("Python Developer" in k for k in backend_kws)
    assert any("FastAPI" in k for k in backend_kws)

    web_kws = DEFAULT_KEYWORD_GROUPS["web_fullstack"]
    assert any("Laravel" in k for k in web_kws)
    assert any("Tailwind" in k for k in web_kws)

    sde_kws = DEFAULT_KEYWORD_GROUPS["software_engineering"]
    assert any("SDE Intern" in k for k in sde_kws)
    assert any("Graduate Engineer Trainee" in k for k in sde_kws)

    data_kws = DEFAULT_KEYWORD_GROUPS["database_data"]
    assert any("SQL" in k for k in data_kws)
    assert any("MySQL" in k for k in data_kws)
    assert any("SQLite" in k for k in data_kws)
    assert any("Junior Data Analyst" in k for k in data_kws)


def test_custom_keyword_groups_override():
    """Verify settings allow overriding or augmenting keyword groups via JSON config."""
    custom_json = json.dumps({"ai_ml": ["Custom AI Specialist", "LLM Fine-Tuner"]})
    settings = Settings(
        APP_ENV="testing",
        KEYWORD_GROUPS_JSON=custom_json,
    )
    groups = settings.get_keyword_groups()
    assert groups["ai_ml"] == ["Custom AI Specialist", "LLM Fine-Tuner"]
    # Unoverridden categories remain intact
    assert "python_backend" in groups


def test_work_mode_detection():
    """Verify accurate detection of remote, hybrid, and on-site work modes."""
    # Remote
    assert "remote" in detect_work_modes(location="Remote", text="Work from anywhere worldwide")
    assert "remote" in detect_work_modes(location="", text="100% remote WFH opportunity")

    # Hybrid
    assert "hybrid" in detect_work_modes(location="New York, NY", text="Hybrid role, 2 days in office")

    # On-site
    modes_onsite = detect_work_modes(location="San Francisco, CA", text="On-site in office required 5 days a week")
    assert "on-site" in modes_onsite


@pytest.mark.asyncio
async def test_search_jobs_work_mode_filtering(test_db_session):
    """Verify JobService.search_jobs correctly filters by remote, hybrid, and on-site."""
    service = JobService(test_db_session)
    # Insert test listings
    await service.save_or_update_job(JobListingCreate(
        title="Remote AI Engineer",
        company="Remote Corp",
        location="Remote",
        description="Build LLM applications from home.",
        application_url="https://remotecorp.example.com/jobs/1",
        source="test",
    ))
    await service.save_or_update_job(JobListingCreate(
        title="Hybrid Backend Developer",
        company="Hybrid Corp",
        location="London",
        description="Hybrid role with flexible office days.",
        application_url="https://hybridcorp.example.com/jobs/2",
        source="test",
    ))
    await service.save_or_update_job(JobListingCreate(
        title="On-site Hardware Engineer",
        company="Lab Corp",
        location="Berlin",
        description="On-site laboratory presence required.",
        application_url="https://labcorp.example.com/jobs/3",
        source="test",
    ))

    # 1. Search remote
    items_remote, count_remote = await service.search_jobs(JobListingFilter(work_mode="remote"))
    assert any(j.company == "Remote Corp" for j in items_remote)

    # 2. Search hybrid
    items_hybrid, count_hybrid = await service.search_jobs(JobListingFilter(work_mode="hybrid"))
    assert any(j.company == "Hybrid Corp" for j in items_hybrid)

    # 3. Search on-site
    items_onsite, count_onsite = await service.search_jobs(JobListingFilter(work_mode="on-site"))
    assert any(j.company == "Lab Corp" for j in items_onsite)


def test_fresher_detection():
    """Verify detection of fresher, intern, trainee, and entry-level positions."""
    is_fresher_1, reasons_1 = detect_fresher_friendly("SDE Intern (Summer 2026)", "Looking for student interns.")
    assert is_fresher_1 is True

    is_fresher_2, reasons_2 = detect_fresher_friendly("Graduate Engineer Trainee", "No experience required, training provided.")
    assert is_fresher_2 is True

    is_fresher_3, reasons_3 = detect_fresher_friendly("Junior Python Developer", "Requires 0-1 year of experience building APIs.")
    assert is_fresher_3 is True

    # Senior role should not be fresher-friendly
    is_senior, _ = detect_fresher_friendly("Senior Staff AI Architect", "Requires 10+ years experience leading teams.")
    assert is_senior is False


def test_technical_synonym_matching():
    """Verify transferable skills match via synonym taxonomy (e.g. FastAPI -> Python, MySQL -> SQL)."""
    candidate_skills = ["FastAPI", "MySQL", "GenAI"]
    job_text = """
    We are looking for a Python Developer who writes complex SQL queries
    and has experience with Large Language Models (LLM) and prompt engineering.
    """
    analysis = match_skills_with_synonyms(candidate_skills, job_text, job_requirements=["Python", "SQL"])
    synonyms = analysis["synonym_matches"]

    assert "FastAPI" in synonyms  # Matches Python in job
    assert "MySQL" in synonyms    # Matches SQL in job
    assert "GenAI" in synonyms    # Matches LLM in job
    assert analysis["total_matched_skills_count"] == 3


def test_fresher_candidate_zero_experience_evaluation(test_db_session):
    """Candidate with zero professional experience applying to entry-level/intern role receives priority."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI", "SQL"],
        candidate_exp_years=0.0,
        candidate_education=["B.S. in Computer Science"],
        job_title="Software Development Engineer Intern",
        job_description="Great internship opportunity for freshers and students. Python, FastAPI, and SQL basics required.",
        job_requirements=["Python", "FastAPI"],
    )
    # Fresher is prioritized and receives full experience credit (100)
    assert result.experience_score == 100.0
    assert result.status in (EligibilityStatus.STRONG_MATCH, EligibilityStatus.PARTIAL_MATCH)
    assert any("fresher" in match.lower() or "intern" in match.lower() for match in result.positive_matches)


def test_partial_match_two_of_ten_skills_not_discarded(test_db_session):
    """If a job asks for ten skills and candidate has two, role is not discarded as INELIGIBLE."""
    engine = MatchingEngine(test_db_session)
    all_ten_reqs = [
        "Python", "FastAPI", "Kubernetes", "AWS", "Kafka",
        "Redis", "Terraform", "Go", "GraphQL", "Datadog"
    ]
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI"],
        candidate_exp_years=0.5,
        candidate_education=["B.S. in Computer Science"],
        job_title="Junior Python / FastAPI Developer",
        job_description="Junior developer role. Must have Python and FastAPI. Nice to have cloud tools.",
        job_requirements=all_ten_reqs,
    )
    # Must NOT be marked INELIGIBLE; must be evaluated as PARTIAL_MATCH
    assert result.status == EligibilityStatus.PARTIAL_MATCH
    assert result.overall_score >= 35.0
    assert any("Python" in p for p in result.positive_matches)


def test_missing_preferred_qualifications_does_not_mark_ineligible(test_db_session):
    """Missing preferred or nice-to-have skills must NEVER mark a job INELIGIBLE."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python", "FastAPI"],
        candidate_exp_years=1.0,
        candidate_education=["B.S. in Computer Science"],
        job_title="Backend Developer",
        job_description="""
        Requirements:
        - Python Developer with FastAPI experience.
        Preferred Qualifications:
        - Nice to have: Rust programming experience.
        - Bonus points for: AWS Certified Solutions Architect.
        - Optional: Docker and Kubernetes.
        """,
        job_requirements=["Python", "FastAPI"],
    )
    # Strong or partial match, definitely not INELIGIBLE
    assert result.status in (EligibilityStatus.STRONG_MATCH, EligibilityStatus.PARTIAL_MATCH)
    assert result.status != EligibilityStatus.INELIGIBLE
    assert len(result.missing_preferred) > 0


def test_strict_senior_experience_requirement_marks_ineligible(test_db_session):
    """A role strictly requiring 8+ years for a Principal/Staff position is marked INELIGIBLE for a fresher."""
    engine = MatchingEngine(test_db_session)
    result = engine._deterministic_evaluation(
        candidate_skills=["Python"],
        candidate_exp_years=0.0,
        candidate_education=["B.S. in Computer Science"],
        job_title="Principal Staff Architect",
        job_description="Mandatory 8+ years of architectural experience leading enterprise distributed systems.",
        job_requirements=["System Architecture", "Leadership"],
    )
    assert result.status == EligibilityStatus.INELIGIBLE
    assert any("experience threshold" in c.lower() or "requires 8" in c.lower() for c in result.missing_criteria)


def test_discover_title_variations():
    """Verify dynamic discovery of job title variations from listing titles."""
    title = "Python Developer / Junior AI Engineer - Remote"
    variations = discover_title_variations(title, existing_keywords=["Python Developer"])
    assert "Junior AI Engineer" in variations or any("AI" in v for v in variations)
