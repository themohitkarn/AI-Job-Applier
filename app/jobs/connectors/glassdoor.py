"""Glassdoor Source Connector (Assisted Job-Link Import & Salary Context).

Compliance & Authorization Notice:
Glassdoor Terms of Use explicitly forbid automated extraction, scraping, and bots.
Partner API access requires enterprise commercial licensing. Direct integration is
supported via authorized Job-Link Import, enabling candidates to import specific job
postings directly for matching, drafting, and assisted application.
"""
from typing import Any, Dict, List, Optional
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate


class GlassdoorConnector(BaseJobConnector):
    """Assisted Job-Link Import and Application Navigator for Glassdoor."""

    @property
    def name(self) -> str:
        return "glassdoor"

    @property
    def display_name(self) -> str:
        return "Glassdoor (Assisted Link Import)"

    @property
    def capabilities(self) -> SourceCapability:
        return SourceCapability(
            source_name=self.name,
            display_name=self.display_name,
            category="assisted_import",
            supports_job_fetching=False,  # Scraping prohibited by Glassdoor Terms of Use
            supports_link_import=True,
            supports_open_application_link=True,
            supports_form_filling=True,
            supports_document_upload=True,
            supports_confirmed_submission=True,
            requires_credentials=False,
            rate_limit_per_minute=10,
            compliance_policy="Automated crawling prohibited by Glassdoor Terms of Use. Supported via user Job-Link Import and assisted browsing.",
            enabled=True,
        )

    async def check_health(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "ready",
            "mode": "assisted_import",
            "supported_features": ["link_import", "metadata_extraction", "form_prefill"],
            "policy_note": self.capabilities.compliance_policy,
        }

    async def fetch_jobs(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobListingCreate]:
        return []
