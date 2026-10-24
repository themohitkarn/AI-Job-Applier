"""Schemas for browser automation and application workflow."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    ANALYZED = "ANALYZED"
    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    ELIGIBLE = "STRONG_MATCH"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DRAFT_READY = "DRAFT_READY"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"


class BrowserActionRequest(BaseModel):
    job_id: int
    resume_id: Optional[int] = None
    draft_id: Optional[int] = None
    user_confirmed_submission: bool = False
    dry_run: bool = True  # If true, fills form fields and stops before submit


class BrowserActionResponse(BaseModel):
    application_id: int
    job_id: int
    status: ApplicationStatus
    last_step: str
    fields_filled: Dict[str, str] = Field(default_factory=dict)
    screenshot_path: Optional[str] = None
    requires_user_approval: bool
    confirmation_reference: Optional[str] = None
    error_message: Optional[str] = None
    message: str
