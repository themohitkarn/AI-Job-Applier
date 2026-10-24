"""Aggregation of all v1 API route handlers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    config,
    generation,
    health,
    jobs,
    matching,
    profile,
    resumes,
    scheduler,
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health.router)
api_v1_router.include_router(config.router)
api_v1_router.include_router(profile.router)
api_v1_router.include_router(resumes.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(matching.router)
api_v1_router.include_router(generation.router)
api_v1_router.include_router(applications.router)
api_v1_router.include_router(scheduler.router)
