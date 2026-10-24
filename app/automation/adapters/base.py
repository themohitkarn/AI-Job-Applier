"""Base interface for site-specific form filling adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class BaseSiteAdapter(ABC):
    """Abstract class for detecting and interacting with job application form structures."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this adapter is specialized for the given job domain."""
        pass

    @abstractmethod
    async def fill_form(
        self,
        page: Any,
        profile_data: Dict[str, Any],
        resume_path: Optional[str] = None,
        cover_letter: Optional[str] = None,
    ) -> Dict[str, str]:
        """Fill ordinary form fields and upload document if requested. Returns dict of filled fields."""
        pass

    @abstractmethod
    async def check_submission_confirmation(self, page: Any) -> Tuple[bool, Optional[str]]:
        """Verify whether application was legitimately submitted and retrieve confirmation code/text."""
        pass
