"""Job matching and eligibility endpoints."""
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobListing, JobMatch
from app.db.session import get_db
from app.matching.engine import MatchingEngine
from app.matching.schemas import JobMatchResponse

router = APIRouter(prefix="/matching", tags=["Matching & Eligibility"])


@router.post("/evaluate/{job_id}", summary="Evaluate candidate match for a specific job")
async def evaluate_job_match(job_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    engine = MatchingEngine(db)
    try:
        match_record = await engine.evaluate_job(job_id)
        # Fetch job title/company for response
        stmt_job = select(JobListing).where(JobListing.id == job_id)
        job = (await db.execute(stmt_job)).scalar_one()

        return {
            "id": match_record.id,
            "job_id": match_record.job_id,
            "job_title": job.title,
            "company": job.company,
            "overall_score": match_record.overall_score,
            "skills_score": match_record.skills_score,
            "experience_score": match_record.experience_score,
            "education_score": match_record.education_score,
            "status": match_record.status,
            "rationale": match_record.rationale,
            "missing_criteria": json.loads(match_record.missing_criteria or "[]"),
            "positive_matches": json.loads(match_record.positive_matches or "[]"),
            "evaluated_at": match_record.evaluated_at.isoformat() if match_record.evaluated_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{job_id}", summary="Retrieve stored match analysis for a job")
async def get_match_for_job(job_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = select(JobMatch).where(JobMatch.job_id == job_id).order_by(JobMatch.id.desc())
    match_record = (await db.execute(stmt)).scalars().first()
    if not match_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No match analysis recorded for this job yet")

    stmt_job = select(JobListing).where(JobListing.id == job_id)
    job = (await db.execute(stmt_job)).scalar_one()

    return {
        "id": match_record.id,
        "job_id": match_record.job_id,
        "job_title": job.title,
        "company": job.company,
        "overall_score": match_record.overall_score,
        "skills_score": match_record.skills_score,
        "experience_score": match_record.experience_score,
        "education_score": match_record.education_score,
        "status": match_record.status,
        "rationale": match_record.rationale,
        "missing_criteria": json.loads(match_record.missing_criteria or "[]"),
        "positive_matches": json.loads(match_record.positive_matches or "[]"),
        "evaluated_at": match_record.evaluated_at.isoformat() if match_record.evaluated_at else None,
    }


@router.get("", summary="List evaluated matches with filtering")
async def list_matches(
    status_filter: Optional[str] = Query(None, description="STRONG_MATCH, PARTIAL_MATCH, NEEDS_REVIEW, or INELIGIBLE"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    query = select(JobMatch, JobListing).join(JobListing, JobMatch.job_id == JobListing.id)
    if status_filter:
        query = query.where(JobMatch.status == status_filter.upper())
    if min_score is not None:
        query = query.where(JobMatch.overall_score >= min_score)

    query = query.order_by(JobMatch.overall_score.desc())
    results = (await db.execute(query)).all()

    output = []
    for match, job in results:
        output.append({
            "id": match.id,
            "job_id": match.job_id,
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "overall_score": match.overall_score,
            "skills_score": match.skills_score,
            "experience_score": match.experience_score,
            "education_score": match.education_score,
            "status": match.status,
            "rationale": match.rationale,
            "missing_criteria": json.loads(match.missing_criteria or "[]"),
            "positive_matches": json.loads(match.positive_matches or "[]"),
        })
    return output
