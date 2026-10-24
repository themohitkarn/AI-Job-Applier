"""Ashby Job Board Connector (Official employer career board public API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_ashby")


class AshbyConnector(BaseJobConnector):
    """Fetches vacancies from employer career pages hosted on Ashby."""

    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"
    USER_AGENT = "AIJobAssistant/1.0 (Direct Employer Discovery; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "ashby"

    @property
    def display_name(self) -> str:
        return "Ashby (Employer Career Boards)"

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
            rate_limit_per_minute=30,
            compliance_policy="Uses official public Ashby Job Board API for employers with public Ashby job boards.",
            enabled=True,
        )

    def _get_target_organizations(self) -> List[str]:
        settings = get_settings()
        orgs_str = getattr(settings, "ashby_organizations", "")
        return [o.strip() for o in orgs_str.split(",") if o.strip()]

    async def check_health(self) -> Dict[str, Any]:
        orgs = self._get_target_organizations()
        if not orgs:
            return {
                "connector": self.name,
                "status": "unconfigured",
                "reachable": True,
                "note": "No organization tokens configured in ASHBY_ORGANIZATIONS.",
            }
        test_org = orgs[0]
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.BASE_URL}/{test_org}")
                return {
                    "connector": self.name,
                    "status": "healthy" if resp.status_code == 200 else f"http_{resp.status_code}",
                    "reachable": resp.status_code == 200,
                    "active_organizations": orgs,
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
        orgs = self._get_target_organizations()
        if not orgs:
            return results

        keyword_tokens = [k.lower().strip() for k in (keywords or "").split(",") if k.strip()]

        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": self.USER_AGENT}) as client:
            for org in orgs:
                if len(results) >= limit:
                    break
                try:
                    url = f"{self.BASE_URL}/{org}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"Ashby organization '{org}' returned status {resp.status_code}")
                        continue

                    data = resp.json()
                    jobs_data = data.get("jobs", [])
                    company_name = org.capitalize()

                    for j in jobs_data:
                        title = j.get("title") or ""
                        if not title:
                            continue

                        loc_name = j.get("location") or "Remote"
                        department = j.get("department") or ""

                        # Filter keywords
                        combined = f"{title} {department} {loc_name}".lower()
                        if keyword_tokens and not any(kw in combined for kw in keyword_tokens):
                            continue

                        app_url = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{org}/{j.get('id')}"

                        job = JobListingCreate(
                            title=title.strip(),
                            company=company_name,
                            location=loc_name,
                            employment_type="Full-time",
                            experience_level="Mid-level",
                            description=f"Role: {title} in {department} at {company_name}",
                            requirements=[department] if department else [],
                            application_url=app_url,
                            posted_date=datetime.now(timezone.utc),
                            source=self.name,
                            external_id=str(j.get("id", "")),
                        )
                        results.append(job)
                        if len(results) >= limit:
                            break

                except Exception as e:
                    logger.error(f"Error fetching Ashby org '{org}': {e}")

        return results
