"""AI-Assisted Profile Intelligence Engine.

Provides deterministic and AI-powered skill normalization, profile completeness
auditing, complementary skill recommendations, and non-destructive approval workflows
with snapshot-based undo/revert capabilities.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProviderError
from app.ai.factory import get_ai_provider
from app.core.logging import get_logger
from app.core.security import sanitize_prompt_input
from app.core.text_cleaner import safe_parse_list
from app.db.models import ProfileSnapshot, UserProfile
from app.profile.schemas import (
    ApplySuggestionsRequest,
    ProfileAuditReport,
    RevertProfileResponse,
    SkillEnhancementSuggestion,
)

logger = get_logger("profile_intelligence")

# Deterministic normalization map: common misspellings, aliases, and casing
CANONICAL_SKILL_MAP: Dict[str, Tuple[str, str]] = {
    # (canonical_name, category)
    # Python & Backend
    "pyhton": ("Python", "Programming Language"),
    "pyton": ("Python", "Programming Language"),
    "phyton": ("Python", "Programming Language"),
    "python3": ("Python", "Programming Language"),
    "python 3": ("Python", "Programming Language"),
    "fast api": ("FastAPI", "Web Framework"),
    "fastapi": ("FastAPI", "Web Framework"),
    "fast-api": ("FastAPI", "Web Framework"),
    "django": ("Django", "Web Framework"),
    "djagno": ("Django", "Web Framework"),
    "flask": ("Flask", "Web Framework"),
    "flsk": ("Flask", "Web Framework"),
    "sqlalchemy": ("SQLAlchemy", "ORM / Database"),
    "sql alchemy": ("SQLAlchemy", "ORM / Database"),
    "pydantic": ("Pydantic", "Library"),

    # Databases
    "postgres": ("PostgreSQL", "Database"),
    "postgresql": ("PostgreSQL", "Database"),
    "postgres sql": ("PostgreSQL", "Database"),
    "psql": ("PostgreSQL", "Database"),
    "mysql": ("MySQL", "Database"),
    "my sql": ("MySQL", "Database"),
    "sqlite": ("SQLite", "Database"),
    "sqlite3": ("SQLite", "Database"),
    "mongodb": ("MongoDB", "Database"),
    "mongo db": ("MongoDB", "Database"),
    "mongo": ("MongoDB", "Database"),
    "redis": ("Redis", "Database / Cache"),
    "reddis": ("Redis", "Database / Cache"),

    # Web & Full Stack
    "react": ("React", "Frontend Framework"),
    "reactjs": ("React", "Frontend Framework"),
    "react.js": ("React", "Frontend Framework"),
    "react js": ("React", "Frontend Framework"),
    "vue": ("Vue.js", "Frontend Framework"),
    "vuejs": ("Vue.js", "Frontend Framework"),
    "vue.js": ("Vue.js", "Frontend Framework"),
    "vue js": ("Vue.js", "Frontend Framework"),
    "node": ("Node.js", "Runtime / Backend"),
    "nodejs": ("Node.js", "Runtime / Backend"),
    "node.js": ("Node.js", "Runtime / Backend"),
    "node js": ("Node.js", "Runtime / Backend"),
    "nextjs": ("Next.js", "Frontend Framework"),
    "next.js": ("Next.js", "Frontend Framework"),
    "next js": ("Next.js", "Frontend Framework"),
    "typescript": ("TypeScript", "Programming Language"),
    "ts": ("TypeScript", "Programming Language"),
    "javascript": ("JavaScript", "Programming Language"),
    "js": ("JavaScript", "Programming Language"),
    "html": ("HTML5", "Markup"),
    "html5": ("HTML5", "Markup"),
    "css": ("CSS3", "Styling"),
    "css3": ("CSS3", "Styling"),
    "tailwind": ("Tailwind CSS", "CSS Framework"),
    "tailwindcss": ("Tailwind CSS", "CSS Framework"),
    "tailwind css": ("Tailwind CSS", "CSS Framework"),
    "bootstrap": ("Bootstrap", "CSS Framework"),

    # AI & ML
    "machine learning": ("Machine Learning", "AI / ML"),
    "ml": ("Machine Learning", "AI / ML"),
    "deep learning": ("Deep Learning", "AI / ML"),
    "dl": ("Deep Learning", "AI / ML"),
    "pytorch": ("PyTorch", "AI Framework"),
    "py torch": ("PyTorch", "AI Framework"),
    "tensorflow": ("TensorFlow", "AI Framework"),
    "tf": ("TensorFlow", "AI Framework"),
    "tensor flow": ("TensorFlow", "AI Framework"),
    "scikit-learn": ("Scikit-Learn", "Machine Learning Library"),
    "sklearn": ("Scikit-Learn", "Machine Learning Library"),
    "scikitlearn": ("Scikit-Learn", "Machine Learning Library"),
    "pandas": ("Pandas", "Data Science Library"),
    "pndas": ("Pandas", "Data Science Library"),
    "numpy": ("NumPy", "Data Science Library"),
    "nmpy": ("NumPy", "Data Science Library"),
    "langchain": ("LangChain", "LLM Framework"),
    "lang chain": ("LangChain", "LLM Framework"),
    "llamaindex": ("LlamaIndex", "LLM Framework"),
    "llama index": ("LlamaIndex", "LLM Framework"),
    "rag": ("RAG", "AI Architecture"),
    "retrieval augmented generation": ("RAG", "AI Architecture"),
    "prompt engineering": ("Prompt Engineering", "AI Technique"),
    "agentic ai": ("Agentic AI", "AI Systems"),
    "ai agents": ("Agentic AI", "AI Systems"),
    "ai agent": ("Agentic AI", "AI Systems"),

    # DevOps & Cloud
    "docker": ("Docker", "Containerization"),
    "dokcer": ("Docker", "Containerization"),
    "doker": ("Docker", "Containerization"),
    "kubernetes": ("Kubernetes", "Orchestration"),
    "k8s": ("Kubernetes", "Orchestration"),
    "kuberentes": ("Kubernetes", "Orchestration"),
    "aws": ("AWS", "Cloud Platform"),
    "amazon web services": ("AWS", "Cloud Platform"),
    "gcp": ("GCP", "Cloud Platform"),
    "google cloud platform": ("GCP", "Cloud Platform"),
    "google cloud": ("GCP", "Cloud Platform"),
    "azure": ("Azure", "Cloud Platform"),
    "ms azure": ("Azure", "Cloud Platform"),
    "git": ("Git", "Version Control"),
    "github": ("GitHub", "Version Control"),
    "git hub": ("GitHub", "Version Control"),
    "gitlab": ("GitLab", "DevOps"),
    "linux": ("Linux", "Operating System"),
    "lnux": ("Linux", "Operating System"),
    "ci/cd": ("CI/CD", "DevOps"),
    "cicd": ("CI/CD", "DevOps"),
    "ci-cd": ("CI/CD", "DevOps"),
    "rest api": ("REST APIs", "Architecture"),
    "restful api": ("REST APIs", "Architecture"),
    "rest apis": ("REST APIs", "Architecture"),
    "graphql": ("GraphQL", "API Technology"),
    "graph ql": ("GraphQL", "API Technology"),
}

# Heuristic recommendations when AI is offline
DEFAULT_RECOMMENDED_STACKS: Dict[str, List[str]] = {
    "python": ["FastAPI", "Docker", "PostgreSQL", "SQLAlchemy", "Git", "REST APIs"],
    "fastapi": ["Docker", "PostgreSQL", "Redis", "Pydantic", "Pytest", "CI/CD"],
    "react": ["TypeScript", "Tailwind CSS", "Next.js", "Git", "REST APIs"],
    "machine learning": ["PyTorch", "Pandas", "NumPy", "Scikit-Learn", "Docker"],
    "rag": ["LangChain", "Vector Databases", "Prompt Engineering", "FastAPI"],
    "agentic ai": ["LangChain", "FastAPI", "Docker", "Python", "Prompt Engineering"],
}


class ProfileIntelligenceService:
    """Service orchestrating profile auditing, skill normalization, and safe updates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def audit_profile(self, profile: UserProfile, use_ai: bool = True) -> ProfileAuditReport:
        """Analyze user profile completeness and generate actionable recommendations."""
        skills = safe_parse_list(profile.skills)
        target_roles = safe_parse_list(profile.target_roles)
        educations = json.loads(profile.educations or "[]") if isinstance(profile.educations, str) else (profile.educations or [])
        experiences = json.loads(profile.experiences or "[]") if isinstance(profile.experiences, str) else (profile.experiences or [])
        pref_locations = safe_parse_list(profile.preferred_locations)

        # 1. Calculate completeness score (0-100)
        score = 0.0
        missing: List[str] = []
        recommendations: List[str] = []

        if profile.full_name and len(profile.full_name.strip()) >= 2:
            score += 10.0
        else:
            missing.append("Full Name")

        if profile.email and "@" in profile.email:
            score += 10.0
        else:
            missing.append("Email Address")

        if profile.phone and len(profile.phone.strip()) >= 5:
            score += 5.0
        else:
            missing.append("Phone Number")

        if profile.location and len(profile.location.strip()) >= 2:
            score += 10.0
        else:
            missing.append("Location / City")

        if profile.headline and len(profile.headline.strip()) >= 5:
            score += 10.0
        else:
            missing.append("Professional Headline")
            recommendations.append("Add a punchy professional headline (e.g., 'Junior Python & AI Developer') to grab recruiters' attention.")

        if profile.summary and len(profile.summary.strip()) >= 20:
            score += 15.0
        else:
            missing.append("Professional Summary")
            recommendations.append("Write a brief 2-3 sentence summary summarizing your core skills, technical passions, and eagerness to contribute.")

        if len(skills) >= 3:
            score += 15.0
        elif len(skills) > 0:
            score += 8.0
            recommendations.append("Add at least 3-5 verified technical skills to improve job matching accuracy.")
        else:
            missing.append("Skills")
            recommendations.append("List your primary programming languages, frameworks, and tools.")

        if len(target_roles) >= 1:
            score += 10.0
        else:
            missing.append("Target Roles")
            recommendations.append("Specify your target job titles (e.g., 'Junior Python Developer', 'AI Engineer Intern') to focus search results.")

        if len(educations) >= 1 or len(experiences) >= 1:
            score += 15.0
        else:
            missing.append("Education or Experience")
            if float(profile.experience_years or 0.0) == 0.0:
                recommendations.append("Fresher tip: Add your degree, academic projects, or coursework under Education or Experience.")
            else:
                recommendations.append("Add your degree, boot camp, or past work experience.")

        # Determine status label
        if score >= 85.0:
            status = "Strong Profile"
        elif score >= 60.0:
            status = "Good (Needs Minor Additions)"
        else:
            status = "Incomplete (Action Needed)"

        # 2. Skill normalization & corrections
        skill_suggestions: List[SkillEnhancementSuggestion] = []
        normalized_skills_set: Set[str] = set()

        for s in skills:
            clean_s = s.strip()
            lookup_key = clean_s.lower()
            if lookup_key in CANONICAL_SKILL_MAP:
                canonical, cat = CANONICAL_SKILL_MAP[lookup_key]
                normalized_skills_set.add(canonical)
                if canonical != clean_s:
                    skill_suggestions.append(
                        SkillEnhancementSuggestion(
                            original_skill=clean_s,
                            suggested_skill=canonical,
                            category=cat,
                            reason=f"Standardize '{clean_s}' to industry-standard canonical naming '{canonical}'.",
                            confidence=0.98,
                            is_correction=True,
                        )
                    )
            else:
                normalized_skills_set.add(clean_s)

        # 3. Complementary skills & target roles recommendations
        recommended_skills: List[str] = []
        suggested_roles: List[str] = []

        # Heuristic recommendations based on active skills
        for norm_s in list(normalized_skills_set):
            lower_s = norm_s.lower()
            if lower_s in DEFAULT_RECOMMENDED_STACKS:
                for candidate in DEFAULT_RECOMMENDED_STACKS[lower_s]:
                    if candidate.lower() not in {x.lower() for x in skills} and candidate not in recommended_skills:
                        recommended_skills.append(candidate)

        # 4. AI-Enhanced suggestions if enabled
        if use_ai and skills:
            try:
                ai = get_ai_provider()
                prompt = f"""
                You are a senior tech recruiter and career advisor.
                Analyze the following candidate profile:
                - Headline: {profile.headline or 'Not specified'}
                - Experience: {profile.experience_years or 0.0} years
                - Skills: {', '.join(skills)}
                - Target Roles: {', '.join(target_roles) if target_roles else 'Not specified'}

                Task:
                1. Identify any non-standard skill spellings, abbreviations, or missing canonical forms.
                2. Suggest 3-5 high-demand complementary skills suitable for this specific experience level.
                3. Suggest 2-3 tailored target role titles that fit freshers / junior roles if experience is low.

                Output format: JSON object with:
                {{
                    "skill_corrections": [
                        {{"original": "str", "suggested": "str", "category": "str", "reason": "str"}}
                    ],
                    "recommended_skills": ["str"],
                    "suggested_roles": ["str"]
                }}
                """
                ai_resp = await ai.generate_text(
                    prompt=prompt,
                    system_prompt="Return ONLY valid JSON matching the requested schema. No code fences or commentary.",
                    temperature=0.2,
                )
                # Parse JSON safely
                import re
                fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", ai_resp, re.DOTALL)
                raw_json = fence.group(1) if fence else (re.search(r"(\{.*\})", ai_resp, re.DOTALL).group(1) if re.search(r"(\{.*\})", ai_resp, re.DOTALL) else "{}")
                parsed = json.loads(raw_json)

                for corr in parsed.get("skill_corrections", []):
                    orig = corr.get("original", "").strip()
                    sugg = corr.get("suggested", "").strip()
                    if orig and sugg and orig.lower() != sugg.lower():
                        if not any(sg.original_skill.lower() == orig.lower() for sg in skill_suggestions):
                            skill_suggestions.append(
                                SkillEnhancementSuggestion(
                                    original_skill=orig,
                                    suggested_skill=sugg,
                                    category=corr.get("category", "General"),
                                    reason=corr.get("reason", f"Normalize '{orig}' to standard industry term."),
                                    confidence=0.90,
                                    is_correction=True,
                                )
                            )

                for sk in parsed.get("recommended_skills", []):
                    sk_clean = sk.strip()
                    if sk_clean and sk_clean.lower() not in {x.lower() for x in skills} and sk_clean not in recommended_skills:
                        recommended_skills.append(sk_clean)

                for r in parsed.get("suggested_roles", []):
                    r_clean = r.strip()
                    if r_clean and r_clean not in suggested_roles:
                        suggested_roles.append(r_clean)

            except Exception as e:
                logger.info(f"AI profile enrichment skipped: {e}. Using deterministic heuristics.")

        # Fallback target role suggestions if empty
        if not suggested_roles:
            if float(profile.experience_years or 0.0) <= 1.0:
                suggested_roles = ["Junior Python Developer", "AI Engineer Intern", "Backend Developer Trainee"]
            else:
                suggested_roles = ["Python Developer", "Backend Engineer", "Software Engineer"]

        # Check if user has snapshot history for undo
        stmt_snap = (
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == profile.id)
            .order_by(desc(ProfileSnapshot.created_at))
            .limit(1)
        )
        last_snap = (await self.db.execute(stmt_snap)).scalar_one_or_none()

        return ProfileAuditReport(
            completeness_score=round(score, 1),
            completeness_status=status,
            missing_sections=missing,
            recommendations=recommendations,
            skill_suggestions=skill_suggestions,
            recommended_skills=recommended_skills[:8],
            suggested_target_roles=suggested_roles[:5],
            can_undo=last_snap is not None,
            last_snapshot_at=last_snap.created_at if last_snap else None,
        )

    async def create_snapshot(self, profile: UserProfile, action_type: str) -> ProfileSnapshot:
        """Save a snapshot of the current profile state before modifications for undo/revert."""
        data = {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "headline": profile.headline,
            "summary": profile.summary,
            "skills": profile.skills,
            "target_roles": profile.target_roles,
            "experience_years": profile.experience_years,
            "experiences": profile.experiences,
            "educations": profile.educations,
            "certifications": profile.certifications,
            "work_authorization": profile.work_authorization,
            "preferred_locations": profile.preferred_locations,
            "salary_expectation": profile.salary_expectation,
        }
        snap = ProfileSnapshot(
            user_id=profile.id,
            action_type=action_type,
            snapshot_data=json.dumps(data),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(snap)
        await self.db.commit()
        await self.db.refresh(snap)
        return snap

    async def apply_approved_suggestions(
        self, profile: UserProfile, req: ApplySuggestionsRequest
    ) -> UserProfile:
        """Apply user-approved suggestions non-destructively with an automatic rollback snapshot."""
        # 1. Create safety snapshot first
        await self.create_snapshot(profile, action_type="apply_suggestions")

        # 2. Apply skill replacements (e.g. 'pyhton' -> 'Python')
        current_skills = safe_parse_list(profile.skills)
        replacement_map = {k.strip().lower(): v.strip() for k, v in req.approved_skill_replacements.items()}

        new_skills: List[str] = []
        for s in current_skills:
            lower = s.strip().lower()
            if lower in replacement_map:
                new_skills.append(replacement_map[lower])
            else:
                new_skills.append(s.strip())

        # 3. Add approved new skills
        existing_skill_lower = {s.lower() for s in new_skills}
        for add_s in req.added_skills:
            clean = add_s.strip()
            if clean and clean.lower() not in existing_skill_lower:
                new_skills.append(clean)
                existing_skill_lower.add(clean.lower())

        profile.skills = json.dumps(new_skills)

        # 4. Add approved target roles
        current_roles = safe_parse_list(profile.target_roles)
        existing_role_lower = {r.lower() for r in current_roles}
        for add_r in req.added_target_roles:
            clean = add_r.strip()
            if clean and clean.lower() not in existing_role_lower:
                current_roles.append(clean)
                existing_role_lower.add(clean.lower())
        profile.target_roles = json.dumps(current_roles)

        # 5. Optional headline & summary updates if provided
        if req.headline is not None and req.headline.strip():
            profile.headline = req.headline.strip()
        if req.summary is not None and req.summary.strip():
            profile.summary = req.summary.strip()

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def revert_last_snapshot(self, profile: UserProfile) -> RevertProfileResponse:
        """Rollback candidate profile to its immediately preceding snapshot state."""
        stmt_snap = (
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == profile.id)
            .order_by(desc(ProfileSnapshot.created_at))
            .limit(1)
        )
        snap = (await self.db.execute(stmt_snap)).scalar_one_or_none()
        if not snap:
            raise ValueError("No prior profile snapshot found to revert to.")

        data = json.loads(snap.snapshot_data)
        profile.full_name = data.get("full_name", profile.full_name)
        profile.email = data.get("email", profile.email)
        profile.phone = data.get("phone", profile.phone)
        profile.location = data.get("location", profile.location)
        profile.headline = data.get("headline", profile.headline)
        profile.summary = data.get("summary", profile.summary)
        profile.skills = data.get("skills", profile.skills)
        profile.target_roles = data.get("target_roles", profile.target_roles)
        profile.experience_years = data.get("experience_years", profile.experience_years)
        profile.experiences = data.get("experiences", profile.experiences)
        profile.educations = data.get("educations", profile.educations)
        profile.certifications = data.get("certifications", profile.certifications)
        profile.work_authorization = data.get("work_authorization", profile.work_authorization)
        profile.preferred_locations = data.get("preferred_locations", profile.preferred_locations)
        profile.salary_expectation = data.get("salary_expectation", profile.salary_expectation)

        # Delete the consumed snapshot
        await self.db.delete(snap)
        await self.db.commit()
        await self.db.refresh(profile)

        return RevertProfileResponse(
            success=True,
            message="Profile state successfully reverted to previous snapshot.",
            restored_at=datetime.now(timezone.utc),
        )
