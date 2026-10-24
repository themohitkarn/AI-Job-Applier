"""Transparent, explainable job matching and eligibility engine with fresher-first prioritization."""
import json
import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProviderError
from app.ai.factory import get_ai_provider
from app.core.config import get_settings
from app.core.keywords import (
    detect_fresher_friendly,
    detect_work_modes,
    match_skills_with_synonyms,
    split_mandatory_vs_preferred,
)
from app.core.logging import get_logger
from app.core.security import sanitize_prompt_input
from app.db.models import JobListing, JobMatch, UserProfile
from app.matching.schemas import EligibilityStatus, MatchAssessment, ScoringWeights

logger = get_logger("matching_engine")


class MatchingEngine:
    """Evaluates candidate suitability against job postings with deep inspection, technical synonyms, and fresher priority."""

    def __init__(self, db: AsyncSession, weights: Optional[ScoringWeights] = None):
        self.db = db
        self.weights = weights or ScoringWeights()
        self.settings = get_settings()

    def _deterministic_evaluation(
        self,
        candidate_skills: List[str],
        candidate_exp_years: float,
        candidate_education: List[str],
        job_title: str,
        job_description: str,
        job_requirements: List[str],
        job_location: Optional[str] = None,
        job_experience_level: Optional[str] = None,
    ) -> MatchAssessment:
        """Perform explainable rule-based matching inspecting full description, synonyms, and fresher priority."""
        job_text = f"{job_title}\n{job_description}\n{' '.join(job_requirements)}".lower()

        # 1. Detect Work Modes & Fresher Friendliness
        work_modes = detect_work_modes(location=job_location, text=job_text)
        is_fresher, fresher_reasons = detect_fresher_friendly(
            title=job_title,
            description=job_description,
            requirements=job_requirements,
            experience_level=job_experience_level,
        )

        # 2. Mandatory vs Preferred Requirements Separation
        mandatory_reqs, preferred_reqs = split_mandatory_vs_preferred(
            description=job_description,
            requirements=job_requirements,
        )

        # 3. Deep Skill Matching with Technical Synonyms across Full Description
        skill_analysis = match_skills_with_synonyms(
            candidate_skills=candidate_skills,
            job_text=job_text,
            job_requirements=job_requirements,
        )
        direct_matches: List[str] = skill_analysis["direct_matches"]
        synonym_matches: Dict[str, str] = skill_analysis["synonym_matches"]
        total_matched = len(direct_matches) + len(synonym_matches)

        # Identify missing mandatory criteria
        missing_mandatory: List[str] = []
        for req in mandatory_reqs:
            req_lower = req.lower()
            if not any(s.lower() in req_lower for s in candidate_skills) and not any(
                term in req_lower for term in skill_analysis["matched_job_terms"]
            ):
                # Only record concise requirements
                clean_req = req[:100].strip()
                if clean_req and clean_req not in missing_mandatory:
                    missing_mandatory.append(clean_req)

        # Identify missing preferred qualifications (never blocking)
        missing_preferred: List[str] = []
        for pref in preferred_reqs:
            pref_lower = pref.lower()
            if not any(s.lower() in pref_lower for s in candidate_skills) and not any(
                term in pref_lower for term in skill_analysis["matched_job_terms"]
            ):
                clean_pref = pref[:100].strip()
                if clean_pref and clean_pref not in missing_preferred:
                    missing_preferred.append(clean_pref)

        # 4. Calculate Skills Score with Fresher & Transferable Skills Flexibility
        if job_requirements:
            matched_explicit_reqs = sum(
                1 for req in job_requirements
                if any(s.lower() in req.lower() for s in candidate_skills)
                or any(term in req.lower() for term in skill_analysis["matched_job_terms"])
            )
            unmatched_reqs_count = len(job_requirements) - matched_explicit_reqs
            req_coverage = (matched_explicit_reqs / max(1, len(job_requirements))) * 100.0
            cand_utilization = (len(direct_matches) / max(1, len(candidate_skills))) * 100.0 if candidate_skills else 50.0
            cand_utilization = min(100.0, max(0.0, cand_utilization))
            raw_skills_score = min(100.0, (req_coverage * 0.70) + (cand_utilization * 0.30))
        else:
            matched_explicit_reqs = total_matched
            unmatched_reqs_count = 0
            raw_skills_score = min(100.0, (total_matched / max(1, len(candidate_skills))) * 100.0) if candidate_skills else 50.0

        raw_skills_score = max(0.0, min(100.0, raw_skills_score))

        # Fresher-friendly flexibility: if job asks for many skills and candidate has 2+ relevant skills,
        # recognize foundational competence without premature discard
        if total_matched >= 2:
            if is_fresher:
                skills_score = max(raw_skills_score, 55.0 + min(25.0, (total_matched - 2) * 8.0))
            else:
                skills_score = max(raw_skills_score, 45.0 + min(20.0, (total_matched - 2) * 6.0))
        elif total_matched == 1:
            skills_score = max(raw_skills_score, 40.0)
        else:
            skills_score = raw_skills_score

        skills_score = max(0.0, min(100.0, skills_score))

        # 5. Experience Years Extraction & Comparison
        exp_match = re.search(r"(\d+)\+?\s*(?:-\s*\d+\s*)?years?(?:\s+of)?(?:\s+[\w\-]+){0,3}\s+experience", job_text)
        required_exp = float(exp_match.group(1)) if exp_match else None

        missing_criteria: List[str] = [f"Missing required skill: {s}" for s in missing_mandatory[:5]]
        positive_matches: List[str] = [f"Matched technical skill: {s}" for s in direct_matches]

        for cand_s, syn_desc in synonym_matches.items():
            positive_matches.append(f"Transferable skill synergy: {cand_s} ({syn_desc})")

        # Fresher-first experience scoring
        if is_fresher:
            # Candidate with 0-1 years applying to fresher/internship role receives full credit
            exp_score = 100.0
            for r in fresher_reasons:
                positive_matches.append(r)
        elif required_exp is not None:
            req_str = f"{int(required_exp)}" if required_exp.is_integer() else f"{required_exp}"
            if candidate_exp_years >= required_exp:
                exp_score = 100.0
                positive_matches.append(f"Meets experience criteria ({candidate_exp_years} yrs >= {req_str} yrs)")
            elif candidate_exp_years >= required_exp - 1:
                exp_score = 75.0
                missing_criteria.append(f"Requires {req_str} years experience; candidate has {candidate_exp_years} years.")
            elif required_exp <= 2.0 and candidate_exp_years <= 1.0:
                # Early career bracket (0-2 years) accessible to freshers/graduates
                exp_score = 70.0
                positive_matches.append(f"Entry-level accessible: accepts early-career candidates (0-{req_str} years)")
            else:
                exp_score = 25.0
                missing_criteria.append(f"Strict experience requirement unmet: requires {req_str} yrs, candidate has {candidate_exp_years} yrs.")
        else:
            # Unspecified experience requirement: do not penalize regular roles without senior in title
            title_lower = job_title.lower()
            if any(s in title_lower for s in ["senior", "lead", "principal", "staff", "director", "head", "manager"]):
                exp_score = 50.0
                missing_criteria.append("Senior/Leadership title indicated without explicit year threshold.")
            else:
                exp_score = 85.0
                positive_matches.append("Role does not mandate senior experience barrier.")

        # 6. Education Check
        edu_score = 80.0
        if "degree" in job_text or "bachelor" in job_text or "master" in job_text:
            if candidate_education:
                edu_score = 100.0
                positive_matches.append("Candidate holds required higher education degree.")
            else:
                edu_score = 50.0
                missing_criteria.append("Degree preference indicated, but candidate profile has no degrees listed.")

        # 7. Weighted Base Computation
        base_overall = (
            (skills_score * self.weights.skills_weight)
            + (exp_score * self.weights.experience_weight)
            + (edu_score * self.weights.education_weight)
        )

        # 8. Fresher Priority Boost
        fresher_bonus = 0.0
        if self.settings.prioritize_freshers and is_fresher:
            fresher_bonus = self.settings.fresher_bonus_score
            positive_matches.append(f"Fresher priority boost (+{fresher_bonus:.0f} pts applied for early-career opportunity)")

        overall = round(max(0.0, min(100.0, base_overall + fresher_bonus)), 1)

        # 9. Eligibility Category Determination (STRONG_MATCH, PARTIAL_MATCH, NEEDS_REVIEW, INELIGIBLE)
        # Missing preferred qualifications NEVER makes a job INELIGIBLE!
        min_threshold = self.settings.min_match_score

        if required_exp is not None and candidate_exp_years < required_exp - 2 and not is_fresher and required_exp >= 3.0:
            status = EligibilityStatus.INELIGIBLE
            req_str = f"{int(required_exp)}" if required_exp.is_integer() else f"{required_exp}"
            rationale = f"Mandatory experience threshold of {req_str} years is significantly above candidate's {candidate_exp_years} years."
            if rationale not in missing_criteria:
                missing_criteria.append(rationale)
        elif total_matched == 0 and overall < min_threshold:
            status = EligibilityStatus.INELIGIBLE
            rationale = "Candidate qualifications and skills do not sufficiently align with job requirements."
        elif job_requirements and unmatched_reqs_count >= len(job_requirements) / 2 and not is_fresher:
            status = EligibilityStatus.NEEDS_REVIEW
            rationale = f"Candidate is missing key required skills ({', '.join(missing_mandatory[:3])}). Manual review required."
        elif job_requirements and unmatched_reqs_count >= len(job_requirements) / 2 and is_fresher:
            # Candidate has foundational skills (e.g. 2 of 10) in an entry-level/fresher role
            status = EligibilityStatus.PARTIAL_MATCH
            rationale = f"Partial match (Fresher Opportunity): strong foundation in {total_matched} key skills with room for on-the-job expansion."
        elif overall >= 70.0 and (total_matched >= 1 or is_fresher):
            status = EligibilityStatus.STRONG_MATCH
            fresher_note = " (Fresher/Entry-Level Prioritized)" if is_fresher else ""
            rationale = f"Strong qualification match{fresher_note} with {total_matched} key skills and background aligned."
        elif overall >= min_threshold or (total_matched >= 2 and is_fresher):
            status = EligibilityStatus.PARTIAL_MATCH
            fresher_note = " (Welcomes freshers/trainees)" if is_fresher else ""
            rationale = f"Partial match{fresher_note}: solid technical foundation with {total_matched} relevant skills. Strong candidate for on-the-job training."
        elif overall >= 30.0:
            status = EligibilityStatus.NEEDS_REVIEW
            rationale = "Marginal qualification alignment. Manual human review recommended to assess specific requirements."
        else:
            status = EligibilityStatus.INELIGIBLE
            rationale = "Candidate qualifications do not sufficiently align with job requirements."

        return MatchAssessment(
            overall_score=overall,
            skills_score=round(skills_score, 1),
            experience_score=round(exp_score, 1),
            education_score=round(edu_score, 1),
            status=status,
            rationale=rationale,
            missing_criteria=missing_criteria,
            missing_preferred=missing_preferred,
            positive_matches=positive_matches,
            synonym_matches=synonym_matches,
            is_fresher_friendly=is_fresher,
            work_modes=work_modes,
        )

    async def evaluate_job(self, job_id: int, user_id: Optional[int] = None) -> JobMatch:
        """Evaluate matching for a job against user profile, persisting the result."""
        # Fetch Job
        stmt_job = select(JobListing).where(JobListing.id == job_id)
        job = (await self.db.execute(stmt_job)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job ID {job_id} not found.")

        # Fetch Profile
        stmt_user = select(UserProfile).order_by(UserProfile.id.asc()).limit(1)
        profile = (await self.db.execute(stmt_user)).scalar_one_or_none()
        if not profile:
            raise ValueError("No user profile exists to match against. Please create a profile first.")

        candidate_skills = json.loads(profile.skills or "[]")
        candidate_exp = float(profile.experience_years or 0.0)
        candidate_edu = [e.get("degree", "") for e in json.loads(profile.educations or "[]")]
        job_reqs = json.loads(job.requirements or "[]")

        # 1. Run deterministic baseline
        baseline = self._deterministic_evaluation(
            candidate_skills=candidate_skills,
            candidate_exp_years=candidate_exp,
            candidate_education=candidate_edu,
            job_title=job.title,
            job_description=job.description,
            job_requirements=job_reqs,
            job_location=job.location,
            job_experience_level=job.experience_level,
        )

        assessment = baseline

        # 2. Enhance with AI interpretation if available
        try:
            ai_provider = get_ai_provider()
            prompt = f"""
            Candidate Profile:
            - Full Name: {profile.full_name}
            - Experience: {candidate_exp} years (Freshers with zero experience are welcomed for entry-level/internships)
            - Skills: {', '.join(candidate_skills)}
            - Education: {', '.join(candidate_education)}
            - Work Authorization: {profile.work_authorization}

            Job Vacancy:
            - Title: {job.title}
            - Company: {job.company}
            - Location: {job.location}
            - Description: {sanitize_prompt_input(job.description, max_chars=3000)}
            - Explicit Requirements: {', '.join(job_reqs)}

            Rule Assessment Baseline:
            - Overall Score: {baseline.overall_score}
            - Skills Score: {baseline.skills_score}
            - Experience Score: {baseline.experience_score}
            - Baseline Status: {baseline.status}
            - Fresher Friendly: {baseline.is_fresher_friendly}

            Instructions:
            - Support result categories: STRONG_MATCH, PARTIAL_MATCH, NEEDS_REVIEW, INELIGIBLE.
            - Prioritize freshers and candidates with 0 professional experience for internships and entry-level roles.
            - Do not mark INELIGIBLE simply because preferred/optional qualifications are missing.
            - Provide a transparent, honest, and explainable technical match assessment.
            """
            ai_assessment = await ai_provider.generate_structured(
                prompt=prompt,
                schema=MatchAssessment,
                system_prompt="You are a transparent, unbiased technical recruiter and job eligibility auditor.",
                temperature=0.1,
            )
            assessment = ai_assessment
        except (AIProviderError, Exception) as e:
            logger.info(f"AI provider unavailable or failed during matching ({e}). Using deterministic assessment.")

        # Persist or update match record
        stmt_match = select(JobMatch).where(JobMatch.job_id == job.id, JobMatch.user_id == profile.id)
        match_record = (await self.db.execute(stmt_match)).scalar_one_or_none()

        if not match_record:
            match_record = JobMatch(
                job_id=job.id,
                user_id=profile.id,
            )
            self.db.add(match_record)

        match_record.overall_score = assessment.overall_score
        match_record.skills_score = assessment.skills_score
        match_record.experience_score = assessment.experience_score
        match_record.education_score = assessment.education_score
        match_record.status = assessment.status.value
        match_record.rationale = assessment.rationale
        match_record.missing_criteria = json.dumps(assessment.missing_criteria)
        match_record.positive_matches = json.dumps(assessment.positive_matches)

        await self.db.commit()
        await self.db.refresh(match_record)
        return match_record
