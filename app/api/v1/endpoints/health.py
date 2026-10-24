"""System and AI health check endpoints."""
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_provider
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", summary="General system readiness check")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Check database connectivity and overall API health."""
    db_status = "unhealthy"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"database_error: {str(e)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "service": "AI Auto Job Apply",
    }


@router.get("/ai", summary="AI Provider status and model verification")
async def ai_health_check() -> Dict[str, Any]:
    """Inspect active AI provider connection and model availability."""
    provider = get_ai_provider()
    health_info = await provider.check_health()
    return health_info
