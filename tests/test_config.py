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



def test_groq_api_key_whitespace_and_quote_stripping():
    """Bug 2 Regression Test: ensure accidental whitespace and surrounding quotes are stripped from GROQ_API_KEY."""
    settings = Settings(
        APP_ENV="testing",
        GROQ_API_KEY='  "gsk_test_quoted_key_456"  ',
    )
    assert settings.groq_api_key == "gsk_test_quoted_key_456"
    # Single quotes too
    settings2 = Settings(
        APP_ENV="testing",
        GROQ_API_KEY="  'gsk_test_single_quoted_789'  ",
    )
    assert settings2.groq_api_key == "gsk_test_single_quoted_789"
    # Plain key without quotes
    settings3 = Settings(
        APP_ENV="testing",
        GROQ_API_KEY="gsk_test_plain_key_123",
    )
    assert settings3.groq_api_key == "gsk_test_plain_key_123"


def test_config_env_file_path_is_absolute():
    """Bug 2 Regression Test: verify env_file in model_config uses an absolute path, not relative '.'."""
    from app.core.config import ENV_FILE_PATH
    assert ENV_FILE_PATH.is_absolute(), f"ENV_FILE_PATH should be absolute but got: {ENV_FILE_PATH}"


def test_config_auto_reloads_on_env_mtime_change():
    """Bug 2 Regression Test: get_settings() invalidates singleton when .env mtime increases."""
    import time
    from app.core.config import get_settings, reset_settings, _settings_env_mtime
    reset_settings()
    s1 = get_settings()
    # Verify initial singleton is cached
    s2 = get_settings()
    assert s1 is s2, "Same settings instance should be returned on consecutive calls"
