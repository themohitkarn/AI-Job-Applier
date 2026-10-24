"""Pydantic schemas for User Profile and Resumes."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class ExperienceItem(BaseModel):
    title: str = Field(..., description="Role title")
    company: str = Field(..., description="Company name")
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str = Field(..., description="Degree or program")
    institution: str = Field(..., description="University / Institution")
    graduation_year: Optional[str] = None


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    target_roles: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    experiences: Optional[List[ExperienceItem]] = None
    educations: Optional[List[EducationItem]] = None
    certifications: Optional[List[str]] = None
    work_authorization: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    salary_expectation: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    location: Optional[str]
    headline: Optional[str]
    summary: Optional[str]
    target_roles: List[str]
    skills: List[str]
    experience_years: float
    experiences: List[ExperienceItem]
    educations: List[EducationItem]
    certifications: List[str]
    work_authorization: Optional[str]
    preferred_locations: List[str]
    salary_expectation: Optional[str]
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    id: int
    filename: str
    file_size_bytes: int
    file_type: str
    extracted_text_preview: str
    is_primary: bool
    created_at: datetime



class SkillEnhancementSuggestion(BaseModel):
    """Proposal for normalizing or correcting a skill."""
    original_skill: str
    suggested_skill: str
    category: str = "General"
    reason: str
    confidence: float = 1.0
    is_correction: bool = True


class ProfileAuditReport(BaseModel):
    """Holistic profile intelligence audit and recommendation report."""
    completeness_score: float = Field(..., ge=0.0, le=100.0)
    completeness_status: str
    missing_sections: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    skill_suggestions: List[SkillEnhancementSuggestion] = Field(default_factory=list)
    recommended_skills: List[str] = Field(default_factory=list)
    suggested_target_roles: List[str] = Field(default_factory=list)
    can_undo: bool = False
    last_snapshot_at: Optional[datetime] = None


class ApplySuggestionsRequest(BaseModel):
    """User-approved modifications to apply to the profile."""
    approved_skill_replacements: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of original skill to accepted canonical replacement (e.g. {'pyhton': 'Python'})"
    )
    added_skills: List[str] = Field(default_factory=list)
    added_target_roles: List[str] = Field(default_factory=list)
    headline: Optional[str] = None
    summary: Optional[str] = None


class RevertProfileResponse(BaseModel):
    """Response returned upon undoing profile modifications."""
    success: bool
    message: str
    restored_at: datetime
