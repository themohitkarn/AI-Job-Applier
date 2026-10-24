"""Arbeitnow Job Source Connector (Documented public tech/remote job board API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.logging import get_logger
from app.core.text_cleaner import clean_html_description
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_arbeitnow")


class ArbeitnowConnector(BaseJobConnector):
    """Fetches vacancies from Arbeitnow's public job board API."""

    API_URL = "https://www.arbeitnow.com/api/job-board-api"
    USER_AGENT = "AIJobAssistant/1.0 (Job Aggregation Platform; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "arbeitnow"

    @property
    def display_name(self) -> str:
        return "Arbeitnow"

    @property
    def capabilities(self) -> SourceCapability:
        return SourceCapability(
            source_name=self.name,
            display_name=self.display_name,
            category="api",
            supports_job_fetching=True,
            supports_link_import=True,
            supports_open_application_link=True,
            supports_form_filling=True,
            supports_document_upload=True,
            supports_confirmed_submission=True,
            requires_credentials=False,
            rate_limit_per_minute=30,
            compliance_policy="Uses Arbeitnow's documented public API with attribution and user-agent identifying headers.",
            enabled=True,
        )

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.API_URL}?page=1")
                return {
                    "connector": self.name,
                    "status": "healthy" if resp.status_code == 200 else f"http_{resp.status_code}",
                    "reachable": resp.status_code == 200,
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
        try:
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": self.USER_AGENT}) as client:
                response = await client.get(self.API_URL)
                if response.status_code != 200:
                    logger.warning(f"Arbeitnow API returned status {response.status_code}")
                    return results

                data = response.json()
                items = data.get("data", [])
                if not isinstance(items, list):
                    return results

                keyword_tokens = [k.lower().strip() for k in (keywords or "").split(",") if k.strip()]

                for item in items:
                    title = item.get("title") or ""
                    company = item.get("company_name") or "Unknown"
                    if not title or not company:
                        continue

                    # Keyword filter if specified
                    tags = item.get("tags") or []
                    desc = item.get("description") or ""
                    combined = f"{title} {desc} {' '.join(tags)}".lower()
                    if keyword_tokens and not any(kw in combined for kw in keyword_tokens):
                        continue

                    posted_date = None
                    if item.get("created_at"):
                        try:
                            posted_date = datetime.fromtimestamp(item["created_at"], tz=timezone.utc)
                        except Exception:
                            posted_date = datetime.now(timezone.utc)

                    url = item.get("url") or ""
                    loc = item.get("location") or ("Remote" if item.get("remote") else "On-site")

                    clean_title = clean_html_description(title.strip())
                    clean_company = clean_html_description(company.strip())
                    clean_desc = clean_html_description(desc)

                    job = JobListingCreate(
                        title=clean_title,
                        company=clean_company,
                        location=loc,
                        employment_type="Full-time",
                        experience_level="Mid-level",
                        salary_currency="USD",
                        description=clean_desc,
                        requirements=[clean_html_description(t) for t in tags],
                        application_url=url,
                        posted_date=posted_date,
                        source=self.name,
                        external_id=str(item.get("slug", "")),
                    )
                    results.append(job)
                    if len(results) >= limit:
                        break

        except Exception as e:
            logger.error(f"Error fetching jobs from Arbeitnow: {e}")
        return results
