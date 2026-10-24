"""Content Generation Service."""
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProviderError
from app.ai.factory import get_ai_provider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import sanitize_prompt_input
from app.db.models import ApplicationDraft, JobListing, UserProfile
from app.generation.cache import ContentCacheManager, compute_generation_fingerprint
from app.generation.schemas import ApproveDraftRequest, DraftType, GenerateContentRequest, GeneratedContentResponse
from app.generation.templates import (
    COLD_EMAIL_USER_TEMPLATE,
    COVER_LETTER_SYSTEM_PROMPT,
    COVER_LETTER_USER_TEMPLATE,
)

logger = get_logger("generation_service")


class ContentService:
    """Orchestrates tailored document generation, fingerprint caching, and approval tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.cache_mgr = ContentCacheManager()

    def _compute_profile_hash(self, profile: UserProfile) -> str:
        """Create a deterministic hash of candidate background."""
        raw = f"{profile.full_name}|{profile.skills}|{profile.experiences}|{profile.educations}|{profile.experience_years}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    async def generate_content(self, req: GenerateContentRequest) -> GeneratedContentResponse:
        """Generate or retrieve cached application material."""
        # Retrieve Job
        stmt_job = select(JobListing).where(JobListing.id == req.job_id)
        job = (await self.db.execute(stmt_job)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job ID {req.job_id} not found.")

        # Retrieve Profile
        stmt_prof = select(UserProfile).order_by(UserProfile.id.asc()).limit(1)
        profile = (await self.db.execute(stmt_prof)).scalar_one_or_none()
        if not profile:
            raise ValueError("No candidate profile found. Create profile before generating application materials.")

        prof_hash = self._compute_profile_hash(profile)
        fingerprint = compute_generation_fingerprint(
            job_id=job.id,
            profile_hash=prof_hash,
            draft_type=req.draft_type.value,
            custom_instructions=req.custom_instructions,
        )

        # Check existing draft if not forced
        if not req.force_regenerate:
            stmt_draft = select(ApplicationDraft).where(
                ApplicationDraft.fingerprint == fingerprint,
                ApplicationDraft.job_id == job.id,
            )
            existing = (await self.db.execute(stmt_draft)).scalar_one_or_none()
            if existing:
                return GeneratedContentResponse(
                    id=existing.id,
                    job_id=job.id,
                    draft_type=existing.draft_type,
                    subject=existing.subject,
                    content=existing.content,
                    qna_answers=json.loads(existing.qna_answers or "{}"),
                    is_approved=existing.is_approved,
                    file_path=existing.file_path,
                    fingerprint=fingerprint,
                    cached=True,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                )

        # Generate via AI
        provider = get_ai_provider()
        candidate_skills = ", ".join(json.loads(profile.skills or "[]"))
        candidate_exp = profile.experiences
        candidate_edu = profile.educations

        if req.draft_type == DraftType.COLD_EMAIL:
            system_prompt = COVER_LETTER_SYSTEM_PROMPT
            user_prompt = COLD_EMAIL_USER_TEMPLATE.format(
                job_title=job.title,
                company_name=job.company,
                job_description=sanitize_prompt_input(job.description, max_chars=1500),
                candidate_name=profile.full_name,
                candidate_skills=candidate_skills,
                candidate_experience=candidate_exp,
                custom_instructions=sanitize_prompt_input(req.custom_instructions or "None", max_chars=500),
            )
        else:  # Default to Cover Letter
            system_prompt = COVER_LETTER_SYSTEM_PROMPT
            user_prompt = COVER_LETTER_USER_TEMPLATE.format(
                job_title=job.title,
                company_name=job.company,
                job_location=job.location or "Remote",
                job_description=sanitize_prompt_input(job.description, max_chars=2500),
                candidate_name=profile.full_name,
                candidate_email=profile.email,
                candidate_phone=profile.phone or "",
                experience_years=profile.experience_years or 0,
                candidate_skills=candidate_skills,
                candidate_experience=candidate_exp,
                candidate_education=candidate_edu,
                custom_instructions=sanitize_prompt_input(req.custom_instructions or "None", max_chars=500),
            )

        try:
            raw_output = await provider.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.6,
            )
        except AIProviderError as e:
            logger.error(f"AI generation failed: {e}")
            raise

        # Parse Subject line if model included it
        subject: Optional[str] = None
        content = raw_output
        if "Subject:" in raw_output:
            parts = raw_output.split("Subject:", 1)[1].split("\n", 1)
            subject = parts[0].strip()
            content = parts[1].strip() if len(parts) > 1 else raw_output
        else:
            subject = f"Application: {job.title} - {profile.full_name}"

        # Save to disk
        out_filename = f"{req.draft_type.value}_{job.id}_{fingerprint[:8]}.txt"
        file_path = self.settings.generated_docs_dir / out_filename
        file_path.write_text(f"Subject: {subject}\n\n{content}", encoding="utf-8")

        # Cache file
        self.cache_mgr.store_cached_file(fingerprint, content)

        # Store draft in DB
        draft = ApplicationDraft(
            job_id=job.id,
            user_id=profile.id,
            draft_type=req.draft_type.value,
            subject=subject,
            content=content,
            fingerprint=fingerprint,
            is_approved=False,
            file_path=str(file_path),
        )
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)

        return GeneratedContentResponse(
            id=draft.id,
            job_id=job.id,
            draft_type=draft.draft_type,
            subject=draft.subject,
            content=draft.content,
            qna_answers={},
            is_approved=draft.is_approved,
            file_path=draft.file_path,
            fingerprint=fingerprint,
            cached=False,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )

    async def approve_draft(self, draft_id: int, req: ApproveDraftRequest) -> ApplicationDraft:
        """Approve and optionally edit draft content."""
        stmt = select(ApplicationDraft).where(ApplicationDraft.id == draft_id)
        draft = (await self.db.execute(stmt)).scalar_one_or_none()
        if not draft:
            raise ValueError(f"Draft ID {draft_id} not found.")

        draft.is_approved = req.is_approved
        if req.edited_content is not None:
            draft.content = req.edited_content.strip()
        if req.edited_subject is not None:
            draft.subject = req.edited_subject.strip()

        # Update disk file if exists
        if draft.file_path:
            p = Path(draft.file_path)
            if p.exists():
                p.write_text(f"Subject: {draft.subject}\n\n{draft.content}", encoding="utf-8")

        await self.db.commit()
        await self.db.refresh(draft)
        return draft
