"""User profile and resume document management service."""
import json
import uuid
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import sanitize_filename, validate_file_path, validate_file_upload
from app.db.models import ResumeDocument, UserProfile
from app.profile.resume_parser import extract_text_from_file
from app.profile.schemas import UserProfileResponse, UserProfileUpdate, ExperienceItem, EducationItem

logger = get_logger("profile_service")


class ProfileService:
    """Manages candidate profile data, resume storage, and parsing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_or_create_profile(self) -> UserProfile:
        """Get the primary user profile, creating a default one if none exists."""
        stmt = select(UserProfile).order_by(UserProfile.id.asc()).limit(1)
        profile = (await self.db.execute(stmt)).scalar_one_or_none()
        if not profile:
            profile = UserProfile(
                full_name="Candidate",
                email="candidate@example.com",
                target_roles=json.dumps(["Software Engineer", "Python Developer"]),
                skills=json.dumps(["Python", "FastAPI", "SQLAlchemy", "Git", "Docker"]),
                experience_years=3.0,
                experiences=json.dumps([{
                    "title": "Software Developer",
                    "company": "Tech Corp",
                    "start_year": "2023",
                    "end_year": "Present",
                    "responsibilities": ["Building microservices with FastAPI", "Designing database schemas"]
                }]),
                educations=json.dumps([{
                    "degree": "Bachelor of Technology in Computer Science",
                    "institution": "University Institute of Technology",
                    "graduation_year": "2023"
                }]),
                certifications=json.dumps([]),
                preferred_locations=json.dumps(["Remote"]),
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
        return profile

    async def update_profile(self, data: UserProfileUpdate) -> UserProfile:
        """Update candidate attributes."""
        profile = await self.get_or_create_profile()
        update_dict = data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field in ("target_roles", "skills", "certifications", "preferred_locations"):
                setattr(profile, field, json.dumps(value))
            elif field in ("experiences", "educations"):
                setattr(profile, field, json.dumps([item for item in value]))
            else:
                setattr(profile, field, value)

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    def format_profile_response(self, profile: UserProfile) -> UserProfileResponse:
        """Convert ORM profile to Pydantic response."""
        return UserProfileResponse(
            id=profile.id,
            full_name=profile.full_name or "",
            email=profile.email or "",
            phone=profile.phone,
            location=profile.location,
            headline=profile.headline,
            summary=profile.summary,
            target_roles=json.loads(profile.target_roles or "[]"),
            skills=json.loads(profile.skills or "[]"),
            experience_years=float(profile.experience_years or 0.0),
            experiences=[ExperienceItem(**e) for e in json.loads(profile.experiences or "[]")],
            educations=[EducationItem(**e) for e in json.loads(profile.educations or "[]")],
            certifications=json.loads(profile.certifications or "[]"),
            work_authorization=profile.work_authorization,
            preferred_locations=json.loads(profile.preferred_locations or "[]"),
            salary_expectation=profile.salary_expectation,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    async def save_resume_file(
        self,
        raw_filename: str,
        content: bytes,
        is_primary: bool = False,
    ) -> ResumeDocument:
        """Validate, store, extract text, and record a resume upload."""
        validate_file_upload(raw_filename, len(content), max_size_mb=self.settings.max_upload_size_mb)
        safe_name = sanitize_filename(raw_filename)
        unique_prefix = uuid.uuid4().hex[:8]
        stored_filename = f"{unique_prefix}_{safe_name}"

        storage_path = validate_file_path(
            self.settings.resume_storage_dir,
            self.settings.resume_storage_dir / stored_filename
        )
        storage_path.write_bytes(content)

        # Extract text content
        extracted_text = extract_text_from_file(storage_path)

        profile = await self.get_or_create_profile()

        # If primary, reset existing primaries
        if is_primary:
            await self.db.execute(
                update(ResumeDocument)
                .where(ResumeDocument.user_id == profile.id)
                .values(is_primary=False)
            )

        doc = ResumeDocument(
            user_id=profile.id,
            filename=safe_name,
            file_path=str(storage_path),
            file_size_bytes=len(content),
            file_type=storage_path.suffix.lower(),
            extracted_text=extracted_text,
            is_primary=is_primary,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_resumes(self) -> List[ResumeDocument]:
        """List all uploaded resumes."""
        profile = await self.get_or_create_profile()
        stmt = select(ResumeDocument).where(ResumeDocument.user_id == profile.id).order_by(ResumeDocument.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_resume_by_id(self, resume_id: int) -> Optional[ResumeDocument]:
        """Fetch a specific resume by ID."""
        stmt = select(ResumeDocument).where(ResumeDocument.id == resume_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def delete_resume(self, resume_id: int) -> bool:
        """Delete resume record and remove file from disk."""
        doc = await self.get_resume_by_id(resume_id)
        if not doc:
            return False
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete resume file from disk: {e}")

        await self.db.delete(doc)
        await self.db.commit()
        return True
