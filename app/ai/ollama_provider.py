"""Ollama AI Provider Implementation (Optional Local Provider)."""
import json
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.ai.base import AIProvider, AIProviderError
from app.core.logging import get_logger

logger = get_logger("ollama_provider")
T = TypeVar("T", bound=BaseModel)


class OllamaProvider(AIProvider):
    """Local AI provider integrating with Ollama REST API via httpx."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2",
        timeout: float = 60.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def check_health(self) -> Dict[str, Any]:
        """Check if local Ollama daemon is reachable and whether configured model is present."""
        url = f"{self._base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check if model or model:latest matches
                    model_installed = any(
                        self._model == m or self._model == m.split(":")[0]
                        for m in models
                    )
                    return {
                        "provider": "ollama",
                        "status": "healthy" if model_installed else "model_missing",
                        "configured": True,
                        "base_url": self._base_url,
                        "model": self._model,
                        "model_installed": model_installed,
                        "installed_models": models,
                        "instructions": None if model_installed else f"Run 'ollama pull {self._model}' to install this model."
                    }
                else:
                    return {
                        "provider": "ollama",
                        "status": "unhealthy",
                        "configured": True,
                        "base_url": self._base_url,
                        "error": f"Ollama returned HTTP status {response.status_code}",
                    }
        except httpx.ConnectError:
            return {
                "provider": "ollama",
                "status": "unavailable",
                "configured": True,
                "base_url": self._base_url,
                "model": self._model,
                "error": f"Cannot connect to Ollama daemon at {self._base_url}. Is Ollama running?",
                "instructions": "Start Ollama with 'ollama serve' or launch the Ollama desktop app.",
            }
        except Exception as e:
            return {
                "provider": "ollama",
                "status": "error",
                "configured": True,
                "base_url": self._base_url,
                "error": str(e),
            }

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        url = f"{self._base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise AIProviderError(
                        f"Ollama error {response.status_code}: {response.text}",
                        provider="ollama",
                        status_code=response.status_code,
                    )
                data = response.json()
                return data.get("response", "").strip()
        except httpx.ConnectError:
            raise AIProviderError(
                f"Could not connect to Ollama at {self._base_url}. Ensure Ollama is running.",
                provider="ollama",
                status_code=503,
                retryable=True,
            )
        except httpx.TimeoutException:
            raise AIProviderError(
                f"Ollama generation timed out after {self._timeout}s.",
                provider="ollama",
                status_code=504,
                retryable=True,
            )
        except Exception as e:
            if isinstance(e, AIProviderError):
                raise
            raise AIProviderError(f"Ollama generation error: {e}", provider="ollama", status_code=500)

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
            + f"\n\nReturn strictly a JSON object conforming to schema:\n{schema_json}"
        )
        url = f"{self._base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "system": augmented_system,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature if temperature is not None else 0.1},
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise AIProviderError(
                        f"Ollama structured error {response.status_code}: {response.text}",
                        provider="ollama",
                        status_code=response.status_code,
                    )
                data = response.json()
                raw_json = data.get("response", "{}")
                parsed = json.loads(raw_json)
                return schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            raise AIProviderError(
                f"Ollama output validation failed for {schema.__name__}: {e}",
                provider="ollama",
                status_code=422,
            )
        except Exception as e:
            if isinstance(e, AIProviderError):
                raise
            raise AIProviderError(f"Ollama structured generation error: {e}", provider="ollama", status_code=500)
