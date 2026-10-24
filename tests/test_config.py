"""Tests for Configuration, Environment, and Secrets Validation."""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_valid_settings_loading():
    """Verify default valid configuration loads correctly."""
    settings = Settings(
        APP_ENV="testing",
        GROQ_API_KEY="gsk_test_valid_key_123",
        AI_PROVIDER="groq",
    )
    assert settings.app_name == "AI Auto Job Apply"
    assert settings.ai_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert "remoteok" in settings.enabled_connectors_list
    assert len(settings.cors_origins_list) > 0


def test_missing_groq_key_in_production_raises_error():
    """Verify missing Groq key in production raises clear ValueError without leaking secrets."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            AI_PROVIDER="groq",
            GROQ_API_KEY="",
        )
    assert "GROQ_API_KEY is not configured" in str(exc_info.value)


def test_ollama_provider_does_not_require_groq_key():
    """Ollama local provider selection should not fail if Groq key is absent."""
    settings = Settings(
        APP_ENV="development",
        AI_PROVIDER="ollama",
        GROQ_API_KEY=None,
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
    )
    assert settings.ai_provider == "ollama"
    assert settings.ollama_base_url == "http://127.0.0.1:11434"


def test_connectors_parsing():
    """Verify comma-separated connectors parse into clean lowercase list."""
    settings = Settings(
        APP_ENV="testing",
        ENABLED_CONNECTORS="RemoteOK, Jobicy, CustomSource",
        GREENHOUSE_BOARDS="gitlab,stripe",
        LEVER_COMPANIES="deliveroo,spotify",
    )
    assert settings.enabled_connectors_list == ["remoteok", "jobicy", "customsource"]
    assert settings.greenhouse_boards == "gitlab,stripe"
    assert settings.lever_companies == "deliveroo,spotify"
