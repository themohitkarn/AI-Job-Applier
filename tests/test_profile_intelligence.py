"""Tests for AI-Assisted Profile Intelligence Engine."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.ai.base import AIProvider
from app.db.models import UserProfile
from app.profile.intelligence import CANONICAL_SKILL_MAP, ProfileIntelligenceService
from app.profile.schemas import ApplySuggestionsRequest


def test_canonical_skill_map_coverage():
    """Verify standard typos, aliases, and tech terms map to canonical entries."""
    assert CANONICAL_SKILL_MAP["pyhton"][0] == "Python"
    assert CANONICAL_SKILL_MAP["fast api"][0] == "FastAPI"
    assert CANONICAL_SKILL_MAP["postgres sql"][0] == "PostgreSQL"
    assert CANONICAL_SKILL_MAP["reactjs"][0] == "React"
    assert CANONICAL_SKILL_MAP["dokcer"][0] == "Docker"
    assert CANONICAL_SKILL_MAP["k8s"][0] == "Kubernetes"
    assert CANONICAL_SKILL_MAP["aws"][0] == "AWS"
    assert CANONICAL_SKILL_MAP["langchain"][0] == "LangChain"


@pytest.mark.asyncio
async def test_profile_completeness_audit_scoring(test_db_session):
    """Verify profile completeness score calculation and missing section detection."""
    intel_service = ProfileIntelligenceService(test_db_session)

    # Incomplete candidate
    incomplete_prof = UserProfile(
        full_name="Sam Coder",
        email="sam@example.com",
        skills='["Python"]',
        experience_years=0.0,
    )
    test_db_session.add(incomplete_prof)
    await test_db_session.commit()
    await test_db_session.refresh(incomplete_prof)

    report = await intel_service.audit_profile(incomplete_prof, use_ai=False)
    assert report.completeness_score < 60.0
    assert "Professional Headline" in report.missing_sections
    assert "Professional Summary" in report.missing_sections
    assert "Target Roles" in report.missing_sections
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_profile_audit_detects_misspellings_and_aliases(test_db_session):
    """Verify audit proposes canonical corrections for non-standard skills."""
    intel_service = ProfileIntelligenceService(test_db_session)

    prof = UserProfile(
        full_name="Priya Sharma",
        email="priya@example.com",
        phone="+919876543210",
        location="Bengaluru, India",
        headline="Software Developer",
        summary="Passionate Python developer building web APIs and AI agent workflows.",
        skills='["pyhton", "fast api", "postgres sql", "Docker"]',
        target_roles='["Python Developer", "Backend Engineer"]',
        experience_years=0.5,
    )
    test_db_session.add(prof)
    await test_db_session.commit()
    await test_db_session.refresh(prof)

    report = await intel_service.audit_profile(prof, use_ai=False)

    suggested_map = {s.original_skill: s.suggested_skill for s in report.skill_suggestions}
    assert suggested_map.get("pyhton") == "Python"
    assert suggested_map.get("fast api") == "FastAPI"
    assert suggested_map.get("postgres sql") == "PostgreSQL"
    assert "Docker" not in suggested_map  # Already canonical, no correction needed


@pytest.mark.asyncio
async def test_apply_suggestions_and_revert_undo_workflow(test_db_session):
    """Verify non-destructive apply workflow with rollback snapshot."""
    intel_service = ProfileIntelligenceService(test_db_session)

    prof = UserProfile(
        full_name="Rohan Verma",
        email="rohan@example.com",
        skills='["pyhton", "FastAPI"]',
        target_roles='["Backend Developer"]',
        headline="Junior Developer",
        experience_years=0.0,
    )
    test_db_session.add(prof)
    await test_db_session.commit()
    await test_db_session.refresh(prof)

    # 1. Apply user-approved suggestions
    req = ApplySuggestionsRequest(
        approved_skill_replacements={"pyhton": "Python"},
        added_skills=["PostgreSQL", "Docker"],
        added_target_roles=["AI Engineer Intern"],
        headline="Junior Python & AI Developer",
    )
    updated = await intel_service.apply_approved_suggestions(prof, req)

    import json
    updated_skills = json.loads(updated.skills)
    assert "Python" in updated_skills
    assert "pyhton" not in updated_skills
    assert "PostgreSQL" in updated_skills
    assert "Docker" in updated_skills
    assert updated.headline == "Junior Python & AI Developer"

    # 2. Verify snapshot was created
    audit_after = await intel_service.audit_profile(updated, use_ai=False)
    assert audit_after.can_undo is True

    # 3. Revert to previous state
    revert_res = await intel_service.revert_last_snapshot(updated)
    assert revert_res.success is True

    # Check that previous values are restored
    restored_skills = json.loads(updated.skills)
    assert "pyhton" in restored_skills
    assert "PostgreSQL" not in restored_skills
    assert updated.headline == "Junior Developer"

    # Verify cannot undo again since history was consumed
    audit_final = await intel_service.audit_profile(updated, use_ai=False)
    assert audit_final.can_undo is False
