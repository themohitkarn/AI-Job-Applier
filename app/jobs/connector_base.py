"""Base interface and capability definitions for job source connectors."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.jobs.schemas import JobListingCreate


class SourceCapability(BaseModel):
    """Explicit capability matrix tracking supported discovery and application features per source."""
    source_name: str = Field(..., description="Unique machine-readable source identifier")
    display_name: str = Field(..., description="Human-readable platform name")
    category: str = Field(..., description="api, feed, ats, or assisted_import")
    supports_job_fetching: bool = Field(..., description="Automated background/on-demand vacancy discovery")
    supports_link_import: bool = Field(..., description="Direct job posting URL import & parsing")
    supports_open_application_link: bool = Field(..., description="Navigation to verified application URL")
    supports_form_filling: bool = Field(..., description="Browser automation field pre-filling")
    supports_document_upload: bool = Field(..., description="Resume and document file upload")
    supports_confirmed_submission: bool = Field(..., description="Automated or assisted submission confirmation check")
    requires_credentials: bool = Field(default=False, description="Whether authentication or API token is required")
    rate_limit_per_minute: int = Field(default=30, description="Respectful request rate limit")
    compliance_policy: str = Field(..., description="Terms of service and legitimate use policy note")
    enabled: bool = Field(default=True, description="Whether connector is currently enabled")


class BaseJobConnector(ABC):
    """Abstract contract for discovering jobs from external platforms."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this connector."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name of the platform."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> SourceCapability:
        """Return declared capabilities matrix for this source."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check if source API endpoint or import mechanism is operational."""
        pass

    @abstractmethod
    async def fetch_jobs(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobListingCreate]:
        """Fetch, parse, and normalize job listings into standardized schemas."""
        pass
