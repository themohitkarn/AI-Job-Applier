"""Lever Postings Connector (Official employer career board public API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.text_cleaner import clean_html_description
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_lever")


class LeverConnector(BaseJobConnector):
    """Fetches vacancies from employer career pages hosted on Lever."""

    BASE_URL = "https://api.lever.co/v0/postings"
    USER_AGENT = "AIJobAssistant/1.0 (Direct Employer Discovery; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "lever"

    @property
    def display_name(self) -> str:
        return "Lever (Employer Career Boards)"

    @property
    def capabilities(self) -> SourceCapability:
        return SourceCapability(
            source_name=self.name,
            display_name=self.display_name,
            category="ats",
            supports_job_fetching=True,
            supports_link_import=True,
            supports_open_application_link=True,
            supports_form_filling=True,
            supports_document_upload=True,
            supports_confirmed_submission=True,
            requires_credentials=False,
            rate_limit_per_minute=40,
            compliance_policy="Uses official public Lever Postings API for employers with published career listings.",
            enabled=True,
        )

    def _get_target_companies(self) -> List[str]:
        settings = get_settings()
        companies_str = getattr(settings, "lever_companies", "")
        return [c.strip() for c in companies_str.split(",") if c.strip()]

    async def check_health(self) -> Dict[str, Any]:
        companies = self._get_target_companies()
        if not companies:
            return {
                "connector": self.name,
                "status": "unconfigured",
                "reachable": True,
                "note": "No employer company tokens configured in LEVER_COMPANIES.",
            }
        test_comp = companies[0]
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.BASE_URL}/{test_comp}?mode=json")
                return {
                    "connector": self.name,
                    "status": "healthy" if resp.status_code == 200 else f"http_{resp.status_code}",
                    "reachable": resp.status_code == 200,
                    "active_companies": companies,
                }
        except Exception as e:
            return {
                "connector": self.name,
                "status": "unreachable",
                "reachable": False,
                "error": str(e),
            }

    async def fetch_jobs(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
    ) -> List[JobListingCreate]:
        results: List[JobListingCreate] = []
        companies = self._get_target_companies()
        if not companies:
            return results

        keyword_tokens = [k.lower().strip() for k in (keywords or "").split(",") if k.strip()]

        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": self.USER_AGENT}) as client:
            for comp in companies:
                if len(results) >= limit:
                    break
                try:
                    url = f"{self.BASE_URL}/{comp}?mode=json"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"Lever company '{comp}' returned status {resp.status_code}")
                        continue

                    items = resp.json()
                    if not isinstance(items, list):
                        continue

                    company_name = comp.capitalize()

                    for j in items:
                        title = j.get("text") or ""
                        if not title:
                            continue

                        categories = j.get("categories") or {}
                        loc_name = categories.get("location") or "Remote"
                        desc = j.get("descriptionPlain") or j.get("description") or ""

                        # Filter keywords
                        combined = f"{title} {desc} {loc_name}".lower()
                        if keyword_tokens and not any(kw in combined for kw in keyword_tokens):
                            continue

                        app_url = j.get("applyUrl") or j.get("hostedUrl") or ""

                        job = JobListingCreate(
                            title=clean_html_description(title.strip()),
                            company=clean_html_description(company_name),
                            location=loc_name,
                            employment_type=categories.get("commitment") or "Full-time",
                            experience_level="Mid-level",
                            description=clean_html_description(desc),
                            requirements=[clean_html_description(categories.get("team"))] if categories.get("team") else [],
                            application_url=app_url,
                            posted_date=datetime.now(timezone.utc),
                            source=self.name,
                            external_id=str(j.get("id", "")),
                        )
                        results.append(job)
                        if len(results) >= limit:
                            break

                except Exception as e:
                    logger.error(f"Error fetching Lever company '{comp}': {e}")

        return results
