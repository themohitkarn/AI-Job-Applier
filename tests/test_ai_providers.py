"""Tests for AI Providers (Groq, Ollama, Fallback, and Factory)."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import BaseModel
import httpx

from app.ai.base import AIProviderError
from app.ai.factory import FallbackAIProvider, get_ai_provider
from app.ai.groq_provider import GroqProvider
from app.ai.ollama_provider import OllamaProvider


class SampleStructuredOutput(BaseModel):
    summary: str
    confidence_score: float


@pytest.mark.asyncio
async def test_groq_text_generation_success():
    """Verify GroqProvider calls chat completion and returns text."""
    provider = GroqProvider(api_key="gsk_test_mock_key", model="llama-3.3-70b-versatile")

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Tailored cover letter text."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    result = await provider.generate_text("Prompt content")
    assert result == "Tailored cover letter text."
    assert mock_client.chat.completions.create.called


@pytest.mark.asyncio
async def test_groq_structured_generation_success():
    """Verify GroqProvider parses and validates structured JSON into Pydantic model."""
    provider = GroqProvider(api_key="gsk_test_mock_key", model="llama-3.3-70b-versatile")

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '```json\n{"summary": "Excellent fit", "confidence_score": 92.5}\n```'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    result = await provider.generate_structured("Evaluate", SampleStructuredOutput)
    assert isinstance(result, SampleStructuredOutput)
    assert result.summary == "Excellent fit"
    assert result.confidence_score == 92.5


@pytest.mark.asyncio
async def test_groq_unconfigured_health():
    """Unconfigured Groq API key returns unconfigured health status."""
    provider = GroqProvider(api_key=None)
    health = await provider.check_health()
    assert health["status"] == "unconfigured"
    assert health["configured"] is False


@pytest.mark.asyncio
async def test_ollama_unavailable_health():
    """When Ollama daemon is unreachable, health check reports unavailable cleanly without crashing."""
    provider = OllamaProvider(base_url="http://127.0.0.1:99999", model="llama3.2")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
        health = await provider.check_health()
        assert health["status"] == "unavailable"
        assert "Cannot connect" in health["error"]
        assert "instructions" in health


@pytest.mark.asyncio
async def test_ollama_structured_generation_mock():
    """Verify OllamaProvider structured generation parses JSON correctly."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="llama3.2")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": '{"summary": "Local Ollama Match", "confidence_score": 88.0}'
    }

    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
        output = await provider.generate_structured("Analyze", SampleStructuredOutput)
        assert output.summary == "Local Ollama Match"
        assert output.confidence_score == 88.0


@pytest.mark.asyncio
async def test_fallback_provider_execution():
    """Verify FallbackAIProvider fails over to secondary when primary raises AIProviderError."""
    primary_mock = MagicMock()
    primary_mock.provider_name = "groq"
    primary_mock.model_name = "llama-3.3-70b-versatile"
    primary_mock.generate_text = AsyncMock(side_effect=AIProviderError("Groq Down", provider="groq"))

    secondary_mock = MagicMock()
    secondary_mock.provider_name = "ollama"
    secondary_mock.model_name = "llama3.2"
    secondary_mock.generate_text = AsyncMock(return_value="Recovered via Ollama text")

    fallback = FallbackAIProvider(primary_mock, secondary_mock)
    result = await fallback.generate_text("Test prompt")
    assert result == "Recovered via Ollama text"
    assert primary_mock.generate_text.called
    assert secondary_mock.generate_text.called
