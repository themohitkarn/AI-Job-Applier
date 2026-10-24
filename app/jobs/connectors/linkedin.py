"""LinkedIn Source Connector (Assisted Job-Link Import & User-Directed Navigation).

Compliance & Authorization Notice:
LinkedIn User Agreement Section 8.2 and Robots.txt strictly prohibit automated scraping,
data harvesting, crawler bots, and unauthorized querying. Public search APIs are restricted
to LinkedIn Talent Solutions enterprise partners. To strictly adhere to legal terms and
security guidelines, bulk scraping is disabled; integration is provided via supported
Job-Link Import, where candidate provides specific LinkedIn vacancy links.
"""
from typing import Any, Dict, List, Optional
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate


class LinkedInConnector(BaseJobConnector):
    """Assisted Job-Link Import and Application Navigator for LinkedIn postings."""

    @property
    def name(self) -> str:
        return "linkedin"

    @property
    def display_name(self) -> str:
        return "LinkedIn (Assisted Link Import)"

    @property
    def capabilities(self) -> SourceCapability:
        return SourceCapability(
            source_name=self.name,
            display_name=self.display_name,
            category="assisted_import",
            supports_job_fetching=False,  # Bulk automated scraping prohibited by LinkedIn ToS
            supports_link_import=True,    # Supported via direct job URL import
            supports_open_application_link=True,
            supports_form_filling=True,
            supports_document_upload=True,
            supports_confirmed_submission=True,
            requires_credentials=False,
            rate_limit_per_minute=10,
            compliance_policy="Automated crawler scraping prohibited by LinkedIn Section 8.2. Supported via authorized user Job-Link Import and assisted browsing.",
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
        # Bulk scraping is prohibited per ToS; returns empty list with notice
        return []
