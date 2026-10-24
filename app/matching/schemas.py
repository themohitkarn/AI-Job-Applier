"""Schemas for job eligibility and matching engine."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EligibilityStatus(str, Enum):
    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INELIGIBLE = "INELIGIBLE"
    # Backwards-compatibility alias:
    ELIGIBLE = "STRONG_MATCH"


class ScoringWeights(BaseModel):
    skills_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    experience_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    education_weight: float = Field(default=0.20, ge=0.0, le=1.0)


class MatchAssessment(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall matching score (0-100)")
    skills_score: float = Field(..., ge=0.0, le=100.0)
    experience_score: float = Field(..., ge=0.0, le=100.0)
    education_score: float = Field(..., ge=0.0, le=100.0)
    status: EligibilityStatus
    rationale: str
    missing_criteria: List[str] = Field(default_factory=list, description="Mandatory criteria missing")
    missing_preferred: List[str] = Field(default_factory=list, description="Optional/preferred skills not present")
    positive_matches: List[str] = Field(default_factory=list)
    synonym_matches: Dict[str, str] = Field(default_factory=dict, description="Transferable skill mappings")
    is_fresher_friendly: bool = Field(default=False)
    work_modes: List[str] = Field(default_factory=list)
    is_fallback: bool = Field(default=False, description="True if AI failed/unavailable and deterministic rule was used")
    low_information_warning: Optional[str] = Field(default=None, description="Warning if job description was incomplete")


class JobMatchResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    overall_score: float
    skills_score: float
    experience_score: float
    education_score: float
    status: EligibilityStatus
    rationale: str
    missing_criteria: List[str]
    missing_preferred: List[str] = Field(default_factory=list)
    positive_matches: List[str]
    synonym_matches: Dict[str, str] = Field(default_factory=dict)
    is_fresher_friendly: bool = Field(default=False)
    work_modes: List[str] = Field(default_factory=list)
    is_fallback: bool = Field(default=False)
    low_information_warning: Optional[str] = Field(default=None)
