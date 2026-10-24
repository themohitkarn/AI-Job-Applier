"""Abstract Base Class for AI Providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProviderError(Exception):
    """Normalized exception for AI provider failures."""
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class AIProvider(ABC):
    """Abstract interface defining required capabilities for AI models."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'groq', 'ollama')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Verify provider availability and return diagnostic status dictionary."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate unstructured natural language text."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Generate validated structured JSON output conforming to a Pydantic schema."""
        pass
