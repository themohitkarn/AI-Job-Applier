"""Application Configuration & Settings Module.

Uses Pydantic BaseSettings for strong typing, environment variable loading,
and startup validation.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.keywords import DEFAULT_KEYWORD_GROUPS


class Settings(BaseSettings):
    """Central application settings validated against environment variables."""

    # --- Application Meta ---
    app_name: str = Field(default="AI Auto Job Apply", alias="APP_NAME")
    app_env: Literal["development", "production", "testing"] = Field(
        default="development", alias="APP_ENV"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    secret_key: str = Field(
        default="replace-with-a-secure-random-secret-key-for-production",
        alias="SECRET_KEY"
    )

    # --- Database Settings ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/job_assistant.db",
        alias="DATABASE_URL"
    )

    # --- AI Provider Settings ---
    ai_provider: Literal["groq", "ollama"] = Field(default="groq", alias="AI_PROVIDER")
    ai_enable_fallback: bool = Field(default=False, alias="AI_ENABLE_FALLBACK")

    # Groq Settings (Default)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_temperature: float = Field(default=0.7, alias="GROQ_TEMPERATURE", ge=0.0, le=2.0)
    groq_max_tokens: int = Field(default=2048, alias="GROQ_MAX_TOKENS", gt=0)
    groq_timeout: float = Field(default=45.0, alias="GROQ_TIMEOUT", gt=0)
    groq_max_retries: int = Field(default=3, alias="GROQ_MAX_RETRIES", ge=0)

    # Ollama Settings (Optional Local)
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")
    ollama_timeout: float = Field(default=60.0, alias="OLLAMA_TIMEOUT", gt=0)

    # --- Job Discovery Settings ---
    enabled_connectors: str = Field(
        default="remoteok,jobicy,arbeitnow,greenhouse", alias="ENABLED_CONNECTORS"
    )
    job_search_keywords: str = Field(
        default="python,developer,engineer,backend,fastapi",
        alias="JOB_SEARCH_KEYWORDS"
    )
    job_search_location: str = Field(default="", alias="JOB_SEARCH_LOCATION")
    allowed_work_modes: str = Field(
        default="remote,hybrid,on-site", alias="ALLOWED_WORK_MODES"
    )
    prioritize_freshers: bool = Field(
        default=True, alias="PRIORITIZE_FRESHERS"
    )
    fresher_bonus_score: float = Field(
        default=15.0, alias="FRESHER_BONUS_SCORE", ge=0.0, le=50.0
    )
    min_match_score: float = Field(
        default=35.0, alias="MIN_MATCH_SCORE", ge=0.0, le=100.0
    )
    keyword_groups_json: Optional[str] = Field(
        default=None, alias="KEYWORD_GROUPS_JSON"
    )
    job_sync_interval_minutes: int = Field(
        default=60, alias="JOB_SYNC_INTERVAL_MINUTES", gt=0
    )
    job_connector_max_results: int = Field(
        default=50, alias="JOB_CONNECTOR_MAX_RESULTS", gt=0
    )
    job_request_timeout: float = Field(
        default=20.0, alias="JOB_REQUEST_TIMEOUT", gt=0
    )

    # Employer ATS Career Board Targets (Comma-separated tokens/identifiers)
    greenhouse_boards: str = Field(
        default="gitlab,cloudflare", alias="GREENHOUSE_BOARDS"
    )
    lever_companies: str = Field(
        default="", alias="LEVER_COMPANIES"
    )
    ashby_organizations: str = Field(
        default="", alias="ASHBY_ORGANIZATIONS"
    )
    smartrecruiters_companies: str = Field(
        default="", alias="SMARTRECRUITERS_COMPANIES"
    )

    # --- Storage Directories ---
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    resume_storage_dir: Path = Field(default=Path("./data/resumes"), alias="RESUME_STORAGE_DIR")
    generated_docs_dir: Path = Field(default=Path("./data/generated"), alias="GENERATED_DOCS_DIR")
    cache_dir: Path = Field(default=Path("./data/cache"), alias="CACHE_DIR")
    screenshots_dir: Path = Field(default=Path("./data/screenshots"), alias="SCREENSHOTS_DIR")
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB", gt=0)

    # --- Browser Automation Settings ---
    browser_headless: bool = Field(default=True, alias="BROWSER_HEADLESS")
    browser_type: str = Field(default="chromium", alias="BROWSER_TYPE")
    browser_timeout_ms: int = Field(default=30000, alias="BROWSER_TIMEOUT_MS", gt=0)
    browser_slow_mo_ms: int = Field(default=100, alias="BROWSER_SLOW_MO_MS", ge=0)
    browser_require_user_approval: bool = Field(
        default=True, alias="BROWSER_REQUIRE_USER_APPROVAL"
    )

    # --- Scheduler Settings ---
    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    scheduler_check_interval_seconds: int = Field(
        default=60, alias="SCHEDULER_CHECK_INTERVAL_SECONDS", gt=0
    )
    scheduler_cache_cleanup_hours: int = Field(
        default=24, alias="SCHEDULER_CACHE_CLEANUP_HOURS", gt=0
    )

    # --- CORS Origins ---
    cors_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000,http://localhost:8501,http://127.0.0.1:8501",
        alias="CORS_ORIGINS"
    )

    # --- Email Preserved from legacy app.py ---
    sender_email: Optional[str] = Field(default="", alias="SENDER_EMAIL")
    sender_password: Optional[str] = Field(default="", alias="SENDER_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Return parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def enabled_connectors_list(self) -> List[str]:
        """Return parsed list of enabled job connectors."""
        return [c.strip().lower() for c in self.enabled_connectors.split(",") if c.strip()]

    @property
    def allowed_work_modes_list(self) -> List[str]:
        """Return parsed list of allowed work modes."""
        return [m.strip().lower() for m in self.allowed_work_modes.split(",") if m.strip()]

    def get_keyword_groups(self) -> Dict[str, List[str]]:
        """Return configurable keyword taxonomy merged with optional environment overrides."""
        groups = {cat: list(keywords) for cat, keywords in DEFAULT_KEYWORD_GROUPS.items()}
        if self.keyword_groups_json:
            try:
                overrides = json.loads(self.keyword_groups_json)
                if isinstance(overrides, dict):
                    for cat, kws in overrides.items():
                        if isinstance(kws, list):
                            groups[cat] = [str(k) for k in kws]
            except Exception:
                pass
        return groups

    def get_all_job_search_keywords(self) -> List[str]:
        """Aggregate unique search terms from base keywords and all keyword groups."""
        terms = [k.strip() for k in self.job_search_keywords.split(",") if k.strip()]
        groups = self.get_keyword_groups()
        for kws in groups.values():
            for kw in kws:
                if kw and kw not in terms:
                    terms.append(kw)
        return terms

    @model_validator(mode="after")
    def validate_provider_and_dirs(self) -> "Settings":
        """Validate active AI provider credentials and ensure directories exist."""
        # Validate Groq API key if groq is the primary provider
        # Note: In testing mode or when Ollama is selected, groq_api_key can be empty
        if self.ai_provider == "groq" and self.app_env != "testing":
            if not self.groq_api_key or not self.groq_api_key.strip():
                # Raise clear configuration error without leaking any secret
                raise ValueError(
                    "Configuration Error: AI_PROVIDER is set to 'groq', but GROQ_API_KEY is not configured or empty. "
                    "Please provide a valid GROQ_API_KEY in your .env file or environment variables."
                )

        # Ensure all storage paths exist
        for directory in [
            self.data_dir,
            self.resume_storage_dir,
            self.generated_docs_dir,
            self.cache_dir,
            self.screenshots_dir,
        ]:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        return self


# Global singleton instance provider
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset cached settings instance (primarily for testing)."""
    global _settings
    _settings = None
