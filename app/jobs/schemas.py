"""Pydantic schemas for Job Discovery and Listings."""
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobListingBase(BaseModel):
    title: str = Field(..., description="Job role title")
    company: str = Field(..., description="Hiring organization")
    location: Optional[str] = Field(default="Remote", description="Job location or Remote")
    employment_type: Optional[str] = Field(default="Full-time")
    experience_level: Optional[str] = Field(default="Mid-level")
    salary_min: Optional[float] = Field(default=None)
    salary_max: Optional[float] = Field(default=None)
    salary_currency: Optional[str] = Field(default="USD")
    description: str = Field(..., description="Full job description text")
    requirements: List[str] = Field(default_factory=list, description="Extracted requirement bullets")
    application_url: str = Field(..., description="Legitimate career link or application URL")
    posted_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    source: str = Field(..., description="Source name (e.g., remoteok, jobicy)")
    external_id: Optional[str] = None

    @field_validator("employment_type", mode="before")
    @classmethod
    def validate_employment_type(cls, v: Any) -> str:
        if isinstance(v, list):
            joined = ", ".join(str(x) for x in v if str(x).strip())
            return joined if joined else "Full-time"
        if v is None:
            return "Full-time"
        return str(v).strip() or "Full-time"

    @field_validator("location", mode="before")
    @classmethod
    def validate_location(cls, v: Any) -> str:
        if isinstance(v, list):
            joined = ", ".join(str(x) for x in v if str(x).strip())
            return joined if joined else "Remote"
        if v is None:
            return "Remote"
        return str(v).strip() or "Remote"

    @field_validator("experience_level", mode="before")
    @classmethod
    def validate_experience_level(cls, v: Any) -> str:
        if isinstance(v, list):
            joined = ", ".join(str(x) for x in v if str(x).strip())
            return joined if joined else "Mid-level"
        if v is None:
            return "Mid-level"
        return str(v).strip() or "Mid-level"


class JobListingCreate(JobListingBase):
    """Payload when creating/inserting a new discovered job."""
    pass


class JobListingResponse(JobListingBase):
    id: int
    fingerprint: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListingFilter(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = Field(default=None, description="Filter by work mode: remote, hybrid, or on-site")
    fresher_only: Optional[bool] = Field(default=False, description="Filter for fresher, intern, and entry-level friendly postings")
    source: Optional[str] = None
    min_salary: Optional[float] = None
    status: Optional[str] = "active"
    sort_by: Optional[str] = Field(default="newest", description="Sorting order: newest, fresher_first, relevance")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class JobLinkImportRequest(BaseModel):
    """Payload to import a job posting directly from a link."""
    url: str = Field(..., description="Legitimate URL from LinkedIn, Internshala, Glassdoor, or employer career page")
    override_title: Optional[str] = Field(default=None, description="Optional manual override for title")
    override_company: Optional[str] = Field(default=None, description="Optional manual override for company name")
    override_description: Optional[str] = Field(default=None, description="Optional manual override for job description")


class JobLinkImportResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str]
    source: str
    application_url: str
    fingerprint: str
    is_new: bool
    message: str
