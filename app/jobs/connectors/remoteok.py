"""RemoteOK Job Source Connector (Legitimate public remote jobs JSON API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.logging import get_logger
from app.core.text_cleaner import clean_html_description
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_remoteok")


class RemoteOKConnector(BaseJobConnector):
    """Fetches public tech vacancies from RemoteOK API."""

    API_URL = "https://remoteok.com/api"
    USER_AGENT = "AIJobAssistant/1.0 (Job Matching Platform; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "remoteok"

    @property
    def display_name(self) -> str:
        return "RemoteOK"

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
            rate_limit_per_minute=20,
            compliance_policy="Uses RemoteOK's publicly exposed JSON feed with descriptive User-Agent header. Respects rate limits.",
            enabled=True,
        )

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(self.API_URL)
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
                    logger.warning(f"RemoteOK API returned status {response.status_code}")
                    return results

                items = response.json()
                if not isinstance(items, list):
                    return results

                keyword_tokens = [k.lower().strip() for k in (keywords or "").split(",") if k.strip()]

                # Item 0 in RemoteOK is disclaimer/metadata
                for item in items[1:]:
                    if not isinstance(item, dict):
                        continue
                    
                    title = item.get("position") or item.get("title") or ""
                    company = item.get("company") or "Unknown"
                    if not title or not company:
                        continue

                    # Keyword matching filter if provided
                    combined_text = f"{title} {item.get('description', '')} {' '.join(item.get('tags', []))}".lower()
                    if keyword_tokens and not any(kw in combined_text for kw in keyword_tokens):
                        continue

                    tags = item.get("tags") or []
                    posted_date = None
                    if item.get("date"):
                        try:
                            posted_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                        except Exception:
                            posted_date = datetime.now(timezone.utc)

                    url = item.get("apply_url") or item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
                    if not url.startswith("http"):
                        url = f"https://remoteok.com{url}"

                    salary_min = float(item.get("salary_min")) if item.get("salary_min") else None
                    salary_max = float(item.get("salary_max")) if item.get("salary_max") else None

                    clean_title = clean_html_description(title.strip())
                    clean_company = clean_html_description(company.strip())
                    clean_desc = clean_html_description(item.get("description") or f"Role: {clean_title} at {clean_company}. Tags: {', '.join(tags)}")

                    job = JobListingCreate(
                        title=clean_title,
                        company=clean_company,
                        location=item.get("location") or "Remote",
                        employment_type="Full-time",
                        experience_level="Mid-level",
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency="USD",
                        description=clean_desc,
                        requirements=tags,
                        application_url=url,
                        posted_date=posted_date,
                        source=self.name,
                        external_id=str(item.get("id", "")),
                    )
                    results.append(job)
                    if len(results) >= limit:
                        break

        except Exception as e:
            logger.error(f"Error fetching jobs from RemoteOK: {e}")
        return results
