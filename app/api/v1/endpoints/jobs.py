"""Job listing discovery, search, and synchronization endpoints."""
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.jobs.connector_base import SourceCapability
from app.jobs.registry import get_job_registry
from app.jobs.schemas import (
    JobLinkImportRequest,
    JobLinkImportResponse,
    JobListingCreate,
    JobListingFilter,
    JobListingResponse,
)
from app.jobs.service import JobService

router = APIRouter(prefix="/jobs", tags=["Job Discovery"])


@router.get("/sources", response_model=List[SourceCapability], summary="Inspect connector registry and capability matrix")
async def list_sources():
    """Returns the capability matrix and legal compliance status across all supported job sources."""
    settings = get_settings()
    registry = get_job_registry()
    return registry.get_capabilities_matrix(settings.enabled_connectors_list)


@router.post("/import", response_model=JobLinkImportResponse, status_code=status.HTTP_201_CREATED, summary="Import job vacancy from URL")
async def import_job_from_link(
    req: JobLinkImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import and normalize a job vacancy from LinkedIn, Internshala, Glassdoor, or employer career page."""
    service = JobService(db)
    try:
        job, is_new = await service.import_job_from_url(
            url=req.url,
            override_title=req.override_title,
            override_company=req.override_company,
            override_description=req.override_description,
        )
        return JobLinkImportResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            source=job.source,
            application_url=job.application_url,
            fingerprint=job.fingerprint,
            is_new=is_new,
            message="Job successfully imported and ready for matching/application." if is_new else "Existing job matched; updated record.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import failed: {str(e)}")


@router.post("/manual", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, summary="Create a manual job entry")
async def create_manual_job(
    job_in: JobListingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually insert an employer vacancy for AI matching and application drafting."""
    service = JobService(db)
    job, is_new = await service.save_or_update_job(job_in)
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "source": job.source,
        "is_new": is_new,
    }


@router.get("", summary="Search, filter, and paginate job postings")
async def list_jobs(
    query: Optional[str] = Query(None, description="Search keyword in title, company, or description"),
    location: Optional[str] = Query(None, description="Location search (empty/unspecified searches worldwide)"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode: remote, hybrid, or on-site"),
    fresher_only: bool = Query(False, description="Filter for fresher, intern, and entry-level positions"),
    source: Optional[str] = Query(None),
    min_salary: Optional[float] = Query(None),
    status: Optional[str] = Query("active"),
    sort_by: Optional[str] = Query("newest", description="Sorting order: newest, fresher_first, relevance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    filters = JobListingFilter(
        query=query,
        location=location,
        work_mode=work_mode,
        fresher_only=fresher_only,
        source=source,
        min_salary=min_salary,
        status=status,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    service = JobService(db)
    items, total = await service.search_jobs(filters)

    job_responses = []
    for j in items:
        latest_match = j.matches[-1] if (hasattr(j, "matches") and j.matches) else None
        job_responses.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "employment_type": j.employment_type,
            "experience_level": j.experience_level,
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "salary_currency": j.salary_currency,
            "description": j.description,
            "requirements": json.loads(j.requirements or "[]"),
            "application_url": j.application_url,
            "posted_date": j.posted_date.isoformat() if j.posted_date else None,
            "deadline": j.deadline.isoformat() if j.deadline else None,
            "source": j.source,
            "external_id": j.external_id,
            "fingerprint": j.fingerprint,
            "status": j.status,
            "match_score": latest_match.overall_score if latest_match else None,
            "match_status": latest_match.status if latest_match else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
        })

    return {
        "items": job_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/{job_id}", summary="Get specific job vacancy details")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    service = JobService(db)
    job = await service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "employment_type": job.employment_type,
        "experience_level": job.experience_level,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "description": job.description,
        "requirements": json.loads(job.requirements or "[]"),
        "application_url": job.application_url,
        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
        "deadline": job.deadline.isoformat() if job.deadline else None,
        "source": job.source,
        "external_id": job.external_id,
        "fingerprint": job.fingerprint,
        "status": job.status,
    }


@router.post("/sync", summary="Trigger synchronization across all enabled job connectors")
async def sync_jobs(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    service = JobService(db)
    records = await service.sync_all_enabled_sources()
    return {
        "sources": [
            {
                "source": r.source,
                "fetched": r.jobs_fetched,
                "parsed": getattr(r, "jobs_parsed", 0),
                "rejected": getattr(r, "jobs_rejected", 0),
                "duplicate": getattr(r, "jobs_duplicate", 0),
                "added": r.jobs_added,
                "status": r.status,
                "error": r.error_message,
            }
            for r in records
        ]
    }


@router.post("/sync/{source}", summary="Trigger synchronization for a specific job source")
async def sync_source_jobs(source: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    service = JobService(db)
    try:
        rec = await service.sync_connector(source)
        return {
            "source": rec.source,
            "fetched": rec.jobs_fetched,
            "parsed": getattr(rec, "jobs_parsed", 0),
            "rejected": getattr(rec, "jobs_rejected", 0),
            "duplicate": getattr(rec, "jobs_duplicate", 0),
            "added": rec.jobs_added,
            "status": rec.status,
            "error": rec.error_message,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
