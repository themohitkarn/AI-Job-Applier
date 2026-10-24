"""SQLAlchemy database models for persistence."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class UserProfile(Base):
    """Candidate profile containing verified background, skills, and preferences."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False, default="")
    email = Column(String(255), nullable=False, default="")
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    headline = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    
    # JSON-encoded structured attributes
    target_roles = Column(Text, nullable=False, default="[]")  # list of strings
    skills = Column(Text, nullable=False, default="[]")        # list of strings
    experience_years = Column(Float, nullable=False, default=0.0)
    experiences = Column(Text, nullable=False, default="[]")   # list of objects: title, company, years, bullets
    educations = Column(Text, nullable=False, default="[]")    # list of objects: degree, institution, year
    certifications = Column(Text, nullable=False, default="[]")# list of strings
    work_authorization = Column(String(100), nullable=True, default="Eligible to work")
    preferred_locations = Column(Text, nullable=False, default="[]")
    salary_expectation = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    resumes = relationship("ResumeDocument", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")


class ResumeDocument(Base):
    """Stored resume document metadata and extracted plain-text content."""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    extracted_text = Column(Text, nullable=False, default="")
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("UserProfile", back_populates="resumes")


class JobListing(Base):
    """Normalized job vacancy discovered from legitimate sources."""
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    employment_type = Column(String(100), nullable=True)
    experience_level = Column(String(100), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), nullable=True, default="USD")
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False, default="[]")
    application_url = Column(String(1000), nullable=False)
    posted_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(50), default="active", index=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    drafts = relationship("ApplicationDraft", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class JobMatch(Base):
    """Transparent matching assessment for candidate vs job."""
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    
    overall_score = Column(Float, nullable=False, default=0.0)
    skills_score = Column(Float, nullable=False, default=0.0)
    experience_score = Column(Float, nullable=False, default=0.0)
    education_score = Column(Float, nullable=False, default=0.0)
    
    # ELIGIBLE, INELIGIBLE, NEEDS_REVIEW
    status = Column(String(50), nullable=False, default="NEEDS_REVIEW")
    rationale = Column(Text, nullable=False, default="")
    missing_criteria = Column(Text, nullable=False, default="[]")
    positive_matches = Column(Text, nullable=False, default="[]")
    evaluated_at = Column(DateTime, default=utc_now)

    job = relationship("JobListing", back_populates="matches")


class ApplicationDraft(Base):
    """AI-generated tailored materials (cover letters, cold emails, screening Q&A)."""
    __tablename__ = "application_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    
    draft_type = Column(String(50), default="cover_letter")  # cover_letter, cold_email, qna
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    qna_answers = Column(Text, nullable=False, default="{}")
    fingerprint = Column(String(64), nullable=False, index=True)
    is_approved = Column(Boolean, default=False)
    file_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    job = relationship("JobListing", back_populates="drafts")


class Application(Base):
    """Application status tracker with strict human approval gates."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    draft_id = Column(Integer, ForeignKey("application_drafts.id"), nullable=True)

    # Workflow status:
    # DISCOVERED -> ANALYZED -> ELIGIBLE/INELIGIBLE/NEEDS_REVIEW ->
    # DRAFT_READY -> READY_FOR_APPROVAL -> SUBMITTED -> CONFIRMED/FAILED/VERIFICATION_REQUIRED
    status = Column(String(50), default="DISCOVERED", index=True)
    requires_approval = Column(Boolean, default=True)
    is_user_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    confirmation_reference = Column(String(255), nullable=True)
    last_step = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    audit_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    job = relationship("JobListing", back_populates="applications")
    user = relationship("UserProfile", back_populates="applications")


class JobSyncRecord(Base):
    """Audit record for external job connector synchronization runs."""
    __tablename__ = "job_sync_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False, index=True)
    jobs_fetched = Column(Integer, default=0)
    jobs_added = Column(Integer, default=0)
    status = Column(String(50), default="PENDING")  # SUCCESS, FAILED, PARTIAL
    error_message = Column(Text, nullable=True)
    sync_started_at = Column(DateTime, default=utc_now)
    sync_completed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Immutable audit trail for security and state changes."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    details = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utc_now, index=True)
