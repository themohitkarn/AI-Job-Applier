"""AI Provider Factory and Fallback Orchestration."""
from typing import Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel

from app.ai.base import AIProvider, AIProviderError
from app.ai.groq_provider import GroqProvider
from app.ai.ollama_provider import OllamaProvider
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ai_factory")
T = TypeVar("T", bound=BaseModel)


class FallbackAIProvider(AIProvider):
    """Wrapper that tries primary provider and transparently falls back to secondary if enabled."""

    def __init__(self, primary: AIProvider, secondary: AIProvider):
        self._primary = primary
        self._secondary = secondary

    @property
    def provider_name(self) -> str:
        return f"{self._primary.provider_name}_with_{self._secondary.provider_name}_fallback"

    @property
    def model_name(self) -> str:
        return f"{self._primary.model_name} (fallback: {self._secondary.model_name})"

    async def check_health(self) -> Dict[str, Any]:
        primary_health = await self._primary.check_health()
        secondary_health = await self._secondary.check_health()
        return {
            "provider": self.provider_name,
            "status": "healthy" if primary_health.get("status") == "healthy" or secondary_health.get("status") == "healthy" else "unhealthy",
            "primary": primary_health,
            "fallback": secondary_health,
        }

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        try:
            return await self._primary.generate_text(prompt, system_prompt, max_tokens, temperature)
        except AIProviderError as e:
            logger.warning(f"Primary provider {self._primary.provider_name} failed: {e}. Attempting fallback...")
            return await self._secondary.generate_text(prompt, system_prompt, max_tokens, temperature)

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        try:
            return await self._primary.generate_structured(prompt, schema, system_prompt, temperature)
        except AIProviderError as e:
            logger.warning(f"Primary provider {self._primary.provider_name} failed: {e}. Attempting fallback...")
            return await self._secondary.generate_structured(prompt, schema, system_prompt, temperature)


def get_ai_provider(provider_name: Optional[str] = None) -> AIProvider:
    """Instantiate and return the configured or requested AI provider."""
    settings = get_settings()
    active_name = (provider_name or settings.ai_provider).lower()

    if active_name == "ollama":
        primary = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
        )
        if settings.ai_enable_fallback and settings.groq_api_key:
            secondary = GroqProvider(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                temperature=settings.groq_temperature,
                max_tokens=settings.groq_max_tokens,
                timeout=settings.groq_timeout,
                max_retries=settings.groq_max_retries,
            )
            return FallbackAIProvider(primary, secondary)
        return primary

    # Default to Groq
    primary = GroqProvider(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        max_tokens=settings.groq_max_tokens,
        timeout=settings.groq_timeout,
        max_retries=settings.groq_max_retries,
    )

    if settings.ai_enable_fallback:
        secondary = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
        )
        return FallbackAIProvider(primary, secondary)

    return primary
