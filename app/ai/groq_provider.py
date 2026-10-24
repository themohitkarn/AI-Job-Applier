"""Groq AI Provider Implementation."""
import json
import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

try:
    from groq import AsyncGroq, GroqError, RateLimitError, AuthenticationError, APIConnectionError
except ImportError:
    AsyncGroq = None  # Handled gracefully if groq library not yet imported
    GroqError = Exception
    RateLimitError = Exception
    AuthenticationError = Exception
    APIConnectionError = Exception

from app.ai.base import AIProvider, AIProviderError
from app.core.logging import get_logger

logger = get_logger("groq_provider")
T = TypeVar("T", bound=BaseModel)


class GroqProvider(AIProvider):
    """Production Groq provider using AsyncGroq client with structured validation."""

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 45.0,
        max_retries: int = 3,
    ):
        self._api_key = api_key
        # Normalize model identifier for aliases (e.g. gpt-oss-120b, gpt oss120b, openai/gpt-oss-120b)
        raw_model = (model or "openai/gpt-oss-120b").strip()
        clean = raw_model.lower().replace(" ", "-").replace("_", "-").replace(":", "-")
        if clean in ("gpt-oss-120b", "openai/gpt-oss-120b", "gpt-oss120b", "gptoss120b", "openai-gpt-oss-120b", "gptoss-120b"):
            self._model = "openai/gpt-oss-120b"
        elif clean in ("gpt-oss-20b", "openai/gpt-oss-20b", "gpt-oss20b", "gptoss20b", "openai-gpt-oss-20b", "gptoss-20b"):
            self._model = "openai/gpt-oss-20b"
        else:
            self._model = raw_model

        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Optional[AsyncGroq] = None

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> AsyncGroq:
        if not self._api_key or not self._api_key.strip():
            raise AIProviderError(
                message="Groq API key is missing. Set GROQ_API_KEY in your .env or environment.",
                provider="groq",
                status_code=401,
                retryable=False,
            )
        if self._client is None:
            if AsyncGroq is None:
                raise AIProviderError(
                    message="Groq library is not installed in the environment.",
                    provider="groq",
                    status_code=500,
                )
            self._client = AsyncGroq(
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._client

    async def check_health(self) -> Dict[str, Any]:
        """Verify API key and connectivity by listing available models."""
        if not self._api_key:
            return {
                "provider": "groq",
                "status": "unconfigured",
                "configured": False,
                "model": self._model,
                "error": "GROQ_API_KEY not configured.",
            }
        try:
            client = self._get_client()
            models_list = await client.models.list()
            available_ids = [m.id for m in models_list.data]
            is_model_available = self._model in available_ids
            return {
                "provider": "groq",
                "status": "healthy" if is_model_available else "model_not_found",
                "configured": True,
                "model": self._model,
                "model_verified": is_model_available,
                "total_available_models": len(available_ids),
            }
        except AuthenticationError as e:
            logger.warning("Groq authentication failed (401 Unauthorized). Check GROQ_API_KEY in .env.")
            return {
                "provider": "groq",
                "status": "unhealthy",
                "configured": True,
                "model": self._model,
                "http_status": 401,
                "error": "Authentication failed: 401 Unauthorized (Invalid GROQ_API_KEY).",
                "actionable_message": "Your GROQ_API_KEY was rejected by Groq. Please verify or update your key in .env from https://console.groq.com/keys.",
            }
        except Exception as e:
            logger.error(f"Groq health check connection error: {e}")
            return {
                "provider": "groq",
                "status": "unhealthy",
                "configured": True,
                "model": self._model,
                "error": f"Connection error: {str(e)}",
                "actionable_message": "Ensure network connectivity and that Groq services are operational.",
            }

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        client = self._get_client()
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature if temperature is not None else self._temperature,
                    max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
                )
                content = response.choices[0].message.content or ""
                return content.strip()
            except RateLimitError as e:
                last_error = e
                logger.warning(f"Groq Rate limit encountered (attempt {attempt + 1}/{self._max_retries + 1})")
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise AIProviderError(f"Groq rate limit exceeded: {e}", provider="groq", status_code=429, retryable=True)
            except AuthenticationError as e:
                raise AIProviderError("Invalid Groq API Key.", provider="groq", status_code=401, retryable=False)
            except APIConnectionError as e:
                last_error = e
                if attempt < self._max_retries:
                    await asyncio.sleep(1.5 ** attempt)
                    continue
                raise AIProviderError(f"Groq connection failure: {e}", provider="groq", status_code=503, retryable=True)
            except Exception as e:
                raise AIProviderError(f"Groq generation error: {e}", provider="groq", status_code=500)
        raise AIProviderError(f"Groq failed after retries: {last_error}", provider="groq", status_code=500)

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_system = (
            (system_prompt or "You are an expert AI assistant.")
            + f"\n\nCRITICAL REQUIREMENT: Return ONLY a valid JSON object matching this schema:\n{schema_json}\n"
            "Do not include any introductory remarks, markdown code fences, or explanations. Only raw JSON."
        )

        for attempt in range(self._max_retries + 1):
            raw_text = await self.generate_text(
                prompt=prompt,
                system_prompt=augmented_system,
                temperature=temperature if temperature is not None else 0.2,
            )
            # Strip markdown if model included code blocks
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            try:
                data = json.loads(clean_text)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as err:
                logger.warning(f"Failed to parse structured output (attempt {attempt + 1}): {err}")
                if attempt < self._max_retries:
                    await asyncio.sleep(1)
                    continue
                raise AIProviderError(
                    f"Model output did not conform to schema {schema.__name__}: {err}",
                    provider="groq",
                    status_code=422,
                )
        raise AIProviderError("Failed to generate structured data", provider="groq", status_code=422)
