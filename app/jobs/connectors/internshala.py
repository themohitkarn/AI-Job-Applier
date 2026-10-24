"""Internshala Source Connector (Assisted Internship/Job Link Import).

Compliance & Authorization Notice:
Internshala Terms of Service prohibit automated data harvesting, scraping, and bots.
Direct integration is implemented strictly via authorized Job-Link Import where the candidate
submits an Internshala link, and the system extracts public preview metadata and pre-fills
the application flow safely.
"""
from typing import Any, Dict, List, Optional
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate


class InternshalaConnector(BaseJobConnector):
    """Assisted Job-Link Import and Application Navigator for Internshala."""

    @property
    def name(self) -> str:
        return "internshala"

    @property
    def display_name(self) -> str:
        return "Internshala (Assisted Link Import)"

    @property
    def capabilities(self) -> SourceCapability:
        return SourceCapability(
            source_name=self.name,
            display_name=self.display_name,
            category="assisted_import",
            supports_job_fetching=False,  # Bulk automated scraping prohibited by Internshala Terms
            supports_link_import=True,
            supports_open_application_link=True,
            supports_form_filling=True,
            supports_document_upload=True,
            supports_confirmed_submission=True,
            requires_credentials=False,
            rate_limit_per_minute=10,
            compliance_policy="Automated bulk harvesting prohibited by Internshala Terms of Use. Supported via user Job-Link Import.",
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
