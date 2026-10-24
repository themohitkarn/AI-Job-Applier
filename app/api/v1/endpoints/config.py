"""Safe system configuration inspection endpoints."""
from typing import Any, Dict
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("", summary="Get safe sanitized system configuration")
async def get_safe_config() -> Dict[str, Any]:
    """Return runtime configuration without leaking API keys or secrets."""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "debug": settings.debug,
        "ai_provider": settings.ai_provider,
        "ai_enable_fallback": settings.ai_enable_fallback,
        "groq_model": settings.groq_model,
        "groq_configured": bool(settings.groq_api_key and settings.groq_api_key.strip()),
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "enabled_connectors": settings.enabled_connectors_list,
        "job_search_keywords": settings.job_search_keywords,
        "job_sync_interval_minutes": settings.job_sync_interval_minutes,
        "browser_headless": settings.browser_headless,
        "browser_require_user_approval": settings.browser_require_user_approval,
        "scheduler_enabled": settings.enable_scheduler,
    }
