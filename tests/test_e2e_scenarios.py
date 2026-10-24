"""End-to-End Verification across the 12 Core Architectural Scenarios."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.base import AIProvider, AIProviderError
from app.ai.groq_provider import GroqProvider
from app.automation.browser import BrowserAutomationService
from app.automation.schemas import ApplicationStatus, BrowserActionRequest
from app.core.config import Settings
from app.core.text_cleaner import safe_parse_list
from app.db.models import Application, JobListing, JobMatch, UserProfile
from app.db.session import get_db
from app.matching.engine import MatchingEngine
from app.matching.schemas import EligibilityStatus, MatchAssessment
from app.profile.intelligence import CANONICAL_SKILL_MAP, ProfileIntelligenceService
from app.profile.schemas import ApplySuggestionsRequest
from main import app


# -----------------------------------------------------------------------------
# Scenario 1: Valid Profile + Healthy Groq AI Matching
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_01_valid_profile_healthy_groq_ai_matching(test_db_session, monkeypatch):
    """Scenario 1: Valid profile + healthy Groq AI matching succeeds with openai/gpt-oss-120b."""
    job = JobListing(
        title="Junior Python Engineer",
        company="AI Vanguard",
        location="Remote",
        description="Seeking an eager Junior Python Engineer with FastAPI and Docker foundations.",
        requirements='["Python", "FastAPI"]',
        application_url="https://aivanguard.example.com/apply/1",
        source="Arbeitnow",
        fingerprint="e2e_sc1_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.return_value = MatchAssessment(
        overall_score=91.0,
        skills_score=95.0,
        experience_score=88.0,
        education_score=85.0,
        status=EligibilityStatus.STRONG_MATCH,
        rationale="Excellent candidate profile with strong Python fundamentals.",
        positive_matches=["Python", "FastAPI"],
        is_fresher_friendly=True,
    )
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)

    assert result.overall_score == 91.0
    assert result.status == "STRONG_MATCH"
    assert result.is_fallback is False
    assert mock_ai.generate_structured.called


# -----------------------------------------------------------------------------
# Scenario 2: Unhealthy Groq Fallback to Deterministic Baseline
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_02_unhealthy_groq_fallback_to_rules(test_db_session, monkeypatch):
    """Scenario 2: When Groq returns 401 or network error, matching gracefully falls back to rules."""
    job = JobListing(
        title="Entry-Level Python Developer",
        company="LocalCorp",
        location="Remote",
        description="Freshers welcome for basic Python backend tasks.",
        requirements='["Python"]',
        application_url="https://localcorp.example.com/apply/2",
        source="Arbeitnow",
        fingerprint="e2e_sc2_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.side_effect = AIProviderError("401 Unauthorized: Invalid API Key", provider="groq", status_code=401)
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)

    assert result.is_fallback is True
    assert "Rule-based fallback" in result.rationale
    assert result.overall_score > 0.0


# -----------------------------------------------------------------------------
# Scenario 3: Reasoning Model Output with Preamble & Commentary
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_03_reasoning_model_preamble_json_parsing():
    """Scenario 3: Model output containing preamble comments and thinking traces parses cleanly."""
    provider = GroqProvider(api_key="gsk_test_key", model="openai/gpt-oss-120b")

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "<think>Analyzing candidate qualifications against job requirements...</think>\n"
        "Here is the evaluation response:\n\n"
        "```json\n"
        '{"overall_score": 87.5, "skills_score": 90.0, "experience_score": 85.0, "education_score": 85.0, "status": "STRONG_MATCH", "rationale": "Strong fit", "is_fresher_friendly": true}\n'
        "```\n"
        "Best regards."
    )
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    assessment = await provider.generate_structured(prompt="Analyze candidate", schema=MatchAssessment)
    assert assessment.overall_score == 87.5
    assert assessment.status == EligibilityStatus.STRONG_MATCH


# -----------------------------------------------------------------------------
# Scenario 4: Profile with Plain-Text Comma-Separated Skills
# -----------------------------------------------------------------------------
def test_scenario_04_legacy_csv_skills_parsed_cleanly():
    """Scenario 4: Skills stored as comma-separated text parse without JSONDecodeError."""
    csv_raw = "Python, FastAPI, PostgreSQL, Docker, Git"
    parsed = safe_parse_list(csv_raw)
    assert len(parsed) == 5
    assert "Python" in parsed
    assert "Docker" in parsed


# -----------------------------------------------------------------------------
# Scenario 5: Profile Completeness Audit
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_05_profile_completeness_audit(test_db_session):
    """Scenario 5: Audit scores completeness and accurately surfaces missing sections."""
    intel = ProfileIntelligenceService(test_db_session)
    partial_user = UserProfile(
        full_name="Karan Malhotra",
        email="karan@example.com",
        skills='["Python"]',
        experience_years=0.0,
    )
    test_db_session.add(partial_user)
    await test_db_session.commit()
    await test_db_session.refresh(partial_user)

    audit = await intel.audit_profile(partial_user, use_ai=False)
    assert audit.completeness_score < 60.0
    assert "Professional Headline" in audit.missing_sections
    assert "Professional Summary" in audit.missing_sections
    assert "Target Roles" in audit.missing_sections


# -----------------------------------------------------------------------------
# Scenario 6: Skill Normalization for Common Typos/Aliases
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_06_skill_normalization_corrections(test_db_session):
    """Scenario 6: Audit identifies typos (pyhton, fast api) and proposes canonical standards."""
    intel = ProfileIntelligenceService(test_db_session)
    user = UserProfile(
        full_name="Ananya Rao",
        email="ananya@example.com",
        skills='["pyhton", "fast api", "postgres sql", "reactjs", "dokcer"]',
        experience_years=1.0,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    audit = await intel.audit_profile(user, use_ai=False)
    corrections = {s.original_skill: s.suggested_skill for s in audit.skill_suggestions}
    assert corrections["pyhton"] == "Python"
    assert corrections["fast api"] == "FastAPI"
    assert corrections["postgres sql"] == "PostgreSQL"
    assert corrections["reactjs"] == "React"
    assert corrections["dokcer"] == "Docker"


# -----------------------------------------------------------------------------
# Scenario 7: Non-Destructive Apply Suggestions & Snapshot Revert (Undo)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_07_undo_revert_profile_workflow(test_db_session):
    """Scenario 7: Propose enhancements, commit them with snapshot, and rollback via revert."""
    intel = ProfileIntelligenceService(test_db_session)
    user = UserProfile(
        full_name="Devendra Singh",
        email="dev@example.com",
        skills='["pyhton"]',
        headline="Programmer",
        experience_years=0.0,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    # Apply approved normalization and additions
    req = ApplySuggestionsRequest(
        approved_skill_replacements={"pyhton": "Python"},
        added_skills=["FastAPI", "Docker"],
        headline="Junior Python & FastAPI Engineer",
    )
    updated = await intel.apply_approved_suggestions(user, req)
    skills = json.loads(updated.skills)
    assert "Python" in skills
    assert "pyhton" not in skills
    assert updated.headline == "Junior Python & FastAPI Engineer"

    # Revert to snapshot
    revert_res = await intel.revert_last_snapshot(updated)
    assert revert_res.success is True

    # Check restored state
    restored_skills = json.loads(updated.skills)
    assert "pyhton" in restored_skills
    assert "Python" not in restored_skills
    assert updated.headline == "Programmer"


# -----------------------------------------------------------------------------
# Scenario 8: Low-Information Job Flagged with Warning
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_08_low_information_job_warning(test_db_session, monkeypatch):
    """Scenario 8: Jobs with minimal descriptions receive a clear low-information warning banner."""
    job = JobListing(
        title="Backend Intern",
        company="BriefStartup",
        location="Remote",
        description="Vacancy: Backend Intern at BriefStartup",
        requirements='[]',
        application_url="https://brief.example.com/apply/intern",
        source="SmartRecruiters",
        fingerprint="e2e_sc8_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.return_value = MatchAssessment(
        overall_score=45.0,
        skills_score=50.0,
        experience_score=50.0,
        education_score=50.0,
        status=EligibilityStatus.NEEDS_REVIEW,
        rationale="Limited data provided in listing.",
    )
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    result = await engine.evaluate_job(job.id)
    assert result.low_information_warning is not None
    assert "limited details" in result.low_information_warning


# -----------------------------------------------------------------------------
# Scenario 9: Match Caching Prevents Redundant AI Invocations
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_09_match_caching_skips_redundant_calls(test_db_session, monkeypatch):
    """Scenario 9: Unchanged job and candidate profile reuses existing match analysis."""
    job = JobListing(
        title="FastAPI Specialist",
        company="FastCorp",
        location="Remote",
        description="Full job description with detailed requirements for FastAPI.",
        requirements='["FastAPI"]',
        application_url="https://fastcorp.example.com/apply/9",
        source="Arbeitnow",
        fingerprint="e2e_sc9_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    mock_ai = AsyncMock(spec=AIProvider)
    mock_ai.generate_structured.return_value = MatchAssessment(
        overall_score=85.0,
        skills_score=90.0,
        experience_score=80.0,
        education_score=80.0,
        status=EligibilityStatus.STRONG_MATCH,
        rationale="Strong match.",
        positive_matches=["FastAPI"],
    )
    monkeypatch.setattr("app.matching.engine.get_ai_provider", lambda: mock_ai)

    engine = MatchingEngine(test_db_session)
    m1 = await engine.evaluate_job(job.id)
    assert mock_ai.generate_structured.call_count == 1

    m2 = await engine.evaluate_job(job.id)
    assert mock_ai.generate_structured.call_count == 1  # Unchanged!
    assert m1.id == m2.id


# -----------------------------------------------------------------------------
# Scenario 10: Dry-Run Application Stops at READY_FOR_APPROVAL
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_10_dry_run_application_stops_at_approval_gate(test_db_session, monkeypatch):
    """Scenario 10: In dry-run mode, form is pre-filled but submission halts awaiting human confirmation."""
    job = JobListing(
        title="Junior Developer",
        company="ApprovalCorp",
        location="Remote",
        description="Junior developer role.",
        application_url="https://approvalcorp.example.com/apply/10",
        source="Arbeitnow",
        fingerprint="e2e_sc10_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    class FakePlaywrightContext:
        async def __aenter__(self):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.screenshot = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html><body><form><input name='name'/></form></body></html>")
            mock_locator = MagicMock()
            mock_locator.first.is_visible = AsyncMock(return_value=False)
            mock_page.locator.return_value = mock_locator
            mock_ctx = MagicMock()
            mock_ctx.new_page = AsyncMock(return_value=mock_page)
            mock_browser = MagicMock()
            mock_browser.new_context = AsyncMock(return_value=mock_ctx)
            mock_browser.close = AsyncMock()
            class FakeChromium:
                async def launch(self, *args, **kwargs):
                    return mock_browser
            class FakeP:
                chromium = FakeChromium()
            return FakeP()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.automation.browser.async_playwright", lambda: FakePlaywrightContext())

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=True, user_confirmed_submission=False)
    resp = await service.execute_application_flow(req)

    assert resp.status == ApplicationStatus.READY_FOR_APPROVAL
    assert resp.requires_user_approval is True
    assert "dry-run" in resp.message.lower() or "awaiting user approval" in resp.last_step.lower()


# -----------------------------------------------------------------------------
# Scenario 11: Confirmed Submission by User Transitions to CONFIRMED
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_11_user_confirmed_submission_proceeds(test_db_session, monkeypatch):
    """Scenario 11: With user_confirmed_submission=True, the application submits and captures confirmation."""
    job = JobListing(
        title="Python Engineer",
        company="ConfirmCorp",
        location="Remote",
        description="Python opening.",
        application_url="https://confirmcorp.example.com/apply/11",
        source="Arbeitnow",
        fingerprint="e2e_sc11_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    class FakePlaywrightContext:
        async def __aenter__(self):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.screenshot = AsyncMock()
            mock_page.wait_for_timeout = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html><body><h1>Thank you for applying!</h1><p>We received your application.</p></body></html>")

            def fake_locator(sel):
                loc = MagicMock()
                if "h1" in sel or "h2" in sel or "h3" in sel:
                    loc.all_inner_texts = AsyncMock(return_value=["Thank you for applying!"])
                    loc.first.is_visible = AsyncMock(return_value=True)
                elif "submit" in sel.lower() or "apply" in sel.lower() or "button" in sel.lower():
                    loc.first.is_visible = AsyncMock(return_value=True)
                    loc.first.click = AsyncMock()
                    loc.all_inner_texts = AsyncMock(return_value=["Thank you for applying!"])
                else:
                    loc.first.is_visible = AsyncMock(return_value=False)
                    loc.all_inner_texts = AsyncMock(return_value=[])
                return loc

            mock_page.locator.side_effect = fake_locator
            mock_ctx = MagicMock()
            mock_ctx.new_page = AsyncMock(return_value=mock_page)
            mock_browser = MagicMock()
            mock_browser.new_context = AsyncMock(return_value=mock_ctx)
            mock_browser.close = AsyncMock()
            class FakeChromium:
                async def launch(self, *args, **kwargs):
                    return mock_browser
            class FakeP:
                chromium = FakeChromium()
            return FakeP()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.automation.browser.async_playwright", lambda: FakePlaywrightContext())

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=False, user_confirmed_submission=True)
    resp = await service.execute_application_flow(req)

    assert resp.status == ApplicationStatus.CONFIRMED
    assert not resp.requires_user_approval
    assert "successfully submitted" in resp.message.lower()


# -----------------------------------------------------------------------------
# Scenario 12: CAPTCHA / Bot Barrier Flags MANUAL_ACTION_REQUIRED
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scenario_12_captcha_sets_manual_action_required(test_db_session, monkeypatch):
    """Scenario 12: Application blocked by bot protection is saved as MANUAL_ACTION_REQUIRED."""
    job = JobListing(
        title="Security Engineer",
        company="ShieldCorp",
        location="Remote",
        description="Security engineer vacancy.",
        application_url="https://shieldcorp.example.com/apply/12",
        source="Arbeitnow",
        fingerprint="e2e_sc12_job",
        posted_date=datetime.now(timezone.utc),
    )
    test_db_session.add(job)
    await test_db_session.commit()
    await test_db_session.refresh(job)

    class FakePlaywrightContext:
        async def __aenter__(self):
            mock_page = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.screenshot = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html><body><div>Please verify you are a human</div></body></html>")
            mock_locator = MagicMock()
            mock_locator.first.is_visible = AsyncMock(return_value=False)
            mock_page.locator.return_value = mock_locator
            mock_ctx = MagicMock()
            mock_ctx.new_page = AsyncMock(return_value=mock_page)
            mock_browser = MagicMock()
            mock_browser.new_context = AsyncMock(return_value=mock_ctx)
            mock_browser.close = AsyncMock()
            class FakeChromium:
                async def launch(self, *args, **kwargs):
                    return mock_browser
            class FakeP:
                chromium = FakeChromium()
            return FakeP()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.automation.browser.async_playwright", lambda: FakePlaywrightContext())

    service = BrowserAutomationService(test_db_session)
    req = BrowserActionRequest(job_id=job.id, dry_run=True)
    resp = await service.execute_application_flow(req)

    assert resp.status == ApplicationStatus.MANUAL_ACTION_REQUIRED
    assert "Bot protection" in resp.message or "challenge detected" in resp.message
