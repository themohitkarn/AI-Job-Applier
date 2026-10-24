"""SmartRecruiters Job Board Connector (Official employer career board public API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_smartrecruiters")


class SmartRecruitersConnector(BaseJobConnector):
    """Fetches vacancies from employer career pages hosted on SmartRecruiters."""

    BASE_URL = "https://api.smartrecruiters.com/v1/companies"
    USER_AGENT = "AIJobAssistant/1.0 (Direct Employer Discovery; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "smartrecruiters"

    @property
    def display_name(self) -> str:
        return "SmartRecruiters (Employer Career Boards)"

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
            compliance_policy="Uses official public SmartRecruiters Postings API for employers with published postings.",
            enabled=True,
        )

    def _get_target_companies(self) -> List[str]:
        settings = get_settings()
        comps_str = getattr(settings, "smartrecruiters_companies", "")
        return [c.strip() for c in comps_str.split(",") if c.strip()]

    async def check_health(self) -> Dict[str, Any]:
        companies = self._get_target_companies()
        if not companies:
            return {
                "connector": self.name,
                "status": "unconfigured",
                "reachable": True,
                "note": "No company identifiers configured in SMARTRECRUITERS_COMPANIES.",
            }
        test_comp = companies[0]
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.BASE_URL}/{test_comp}/postings?limit=1")
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
                    url = f"{self.BASE_URL}/{comp}/postings?limit={limit}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"SmartRecruiters company '{comp}' returned status {resp.status_code}")
                        continue

                    data = resp.json()
                    postings = data.get("content", [])
                    company_name = comp.capitalize()

                    for j in postings:
                        title = j.get("name") or ""
                        if not title:
                            continue

                        loc_dict = j.get("location") or {}
                        loc_name = loc_dict.get("city") or loc_dict.get("country") or "Remote"

                        # Filter keywords
                        combined = f"{title} {loc_name}".lower()
                        if keyword_tokens and not any(kw in combined for kw in keyword_tokens):
                            continue

                        app_url = f"https://jobs.smartrecruiters.com/{comp}/{j.get('id')}"

                        job = JobListingCreate(
                            title=title.strip(),
                            company=company_name,
                            location=loc_name,
                            employment_type="Full-time",
                            experience_level="Mid-level",
                            description=f"Vacancy: {title} at {company_name}",
                            requirements=[],
                            application_url=app_url,
                            posted_date=datetime.now(timezone.utc),
                            source=self.name,
                            external_id=str(j.get("id", "")),
                        )
                        results.append(job)
                        if len(results) >= limit:
                            break

                except Exception as e:
                    logger.error(f"Error fetching SmartRecruiters company '{comp}': {e}")

        return results
