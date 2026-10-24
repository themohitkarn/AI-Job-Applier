"""User profile management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.profile.intelligence import ProfileIntelligenceService
from app.profile.schemas import (
    ApplySuggestionsRequest,
    ProfileAuditReport,
    RevertProfileResponse,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.profile.service import ProfileService

router = APIRouter(prefix="/profile", tags=["Candidate Profile"])


@router.get("", response_model=UserProfileResponse, summary="Retrieve candidate profile")
async def get_profile(db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    profile = await service.get_or_create_profile()
    return service.format_profile_response(profile)


@router.put("", response_model=UserProfileResponse, summary="Update candidate profile")
async def update_profile(data: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    updated = await service.update_profile(data)
    return service.format_profile_response(updated)


@router.get("/audit", response_model=ProfileAuditReport, summary="Audit profile completeness and get AI suggestions")
async def audit_profile(
    use_ai: bool = Query(default=True, description="Whether to include LLM-based skill enrichment"),
    db: AsyncSession = Depends(get_db)
):
    prof_service = ProfileService(db)
    profile = await prof_service.get_or_create_profile()
    intel_service = ProfileIntelligenceService(db)
    return await intel_service.audit_profile(profile, use_ai=use_ai)


@router.post("/apply-suggestions", response_model=UserProfileResponse, summary="Apply user-approved suggestions non-destructively")
async def apply_suggestions(
    req: ApplySuggestionsRequest,
    db: AsyncSession = Depends(get_db)
):
    prof_service = ProfileService(db)
    profile = await prof_service.get_or_create_profile()
    intel_service = ProfileIntelligenceService(db)
    updated = await intel_service.apply_approved_suggestions(profile, req)
    return prof_service.format_profile_response(updated)


@router.post("/revert", response_model=RevertProfileResponse, summary="Undo last profile modifications and restore previous snapshot")
async def revert_profile(db: AsyncSession = Depends(get_db)):
    prof_service = ProfileService(db)
    profile = await prof_service.get_or_create_profile()
    intel_service = ProfileIntelligenceService(db)
    try:
        return await intel_service.revert_last_snapshot(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

