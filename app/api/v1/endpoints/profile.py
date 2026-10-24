"""User profile management endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.profile.schemas import UserProfileResponse, UserProfileUpdate
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
