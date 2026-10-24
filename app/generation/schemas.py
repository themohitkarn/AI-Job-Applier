"""Schemas for application content generation and drafts."""
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class DraftType(str, Enum):
    COVER_LETTER = "cover_letter"
    COLD_EMAIL = "cold_email"
    QNA_ANSWERS = "qna_answers"
    MATCH_SUMMARY = "match_summary"


class GenerateContentRequest(BaseModel):
    job_id: int
    draft_type: DraftType = DraftType.COVER_LETTER
    custom_instructions: Optional[str] = None
    force_regenerate: bool = False


class GeneratedContentResponse(BaseModel):
    id: int
    job_id: int
    draft_type: str
    subject: Optional[str] = None
    content: str
    qna_answers: Dict[str, str] = Field(default_factory=dict)
    is_approved: bool
    file_path: Optional[str] = None
    fingerprint: str
    cached: bool = False
    created_at: datetime
    updated_at: datetime


class ApproveDraftRequest(BaseModel):
    is_approved: bool = True
    edited_content: Optional[str] = None
    edited_subject: Optional[str] = None
