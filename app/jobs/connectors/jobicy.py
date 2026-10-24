"""Jobicy Job Source Connector (Legitimate public remote tech jobs API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.logging import get_logger
from app.core.text_cleaner import clean_html_description
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_jobicy")


class JobicyConnector(BaseJobConnector):
    """Fetches public remote vacancies from Jobicy API."""

    API_URL = "https://jobicy.com/api/v2/remote-jobs"
    USER_AGENT = "AIJobAssistant/1.0 (Job Aggregation & AI Matching Platform)"

    @property
    def name(self) -> str:
        return "jobicy"

    @property
    def display_name(self) -> str:
        return "Jobicy"

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
            compliance_policy="Uses Jobicy public remote jobs v2 API within query parameters and pagination limits.",
            enabled=True,
        )

    async def check_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.API_URL}?count=1")
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
            params = {"count": min(limit, 50)}
            if keywords:
                primary_kw = keywords.split(",")[0].strip()
                if primary_kw:
                    params["tag"] = primary_kw

            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": self.USER_AGENT}) as client:
                response = await client.get(self.API_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"Jobicy API returned status {response.status_code}")
                    return results

                data = response.json()
                items = data.get("jobs", [])
                if not isinstance(items, list):
                    return results

                for item in items:
                    title = item.get("jobTitle") or ""
                    company = item.get("companyName") or "Unknown"
                    if not title or not company:
                        continue

                    pub_date = None
                    if item.get("pubDate"):
                        try:
                            pub_date = datetime.fromisoformat(item["pubDate"].replace("Z", "+00:00"))
                        except Exception:
                            pub_date = datetime.now(timezone.utc)

                    url = item.get("url") or ""
                    sal_min = float(item["annualSalaryMin"]) if item.get("annualSalaryMin") else None
                    sal_max = float(item["annualSalaryMax"]) if item.get("annualSalaryMax") else None

                    clean_title = clean_html_description(title.strip())
                    clean_company = clean_html_description(company.strip())
                    clean_desc = clean_html_description(item.get("jobDescription") or f"Position: {clean_title} at {clean_company}")

                    # Safely handle jobIndustry whether it's a list or string
                    job_ind = item.get("jobIndustry")
                    if isinstance(job_ind, list):
                        clean_reqs = [clean_html_description(str(x)) for x in job_ind if str(x).strip()]
                    elif isinstance(job_ind, str) and job_ind.strip():
                        clean_reqs = [clean_html_description(job_ind)]
                    else:
                        clean_reqs = []

                    # Safely handle jobType, jobGeo, jobLevel whether list or string
                    job_type_raw = item.get("jobType")
                    if isinstance(job_type_raw, list):
                        job_type = ", ".join(str(x) for x in job_type_raw if str(x).strip()) or "Full-time"
                    else:
                        job_type = str(job_type_raw).strip() if job_type_raw else "Full-time"

                    job_geo_raw = item.get("jobGeo")
                    if isinstance(job_geo_raw, list):
                        job_geo = ", ".join(str(x) for x in job_geo_raw if str(x).strip()) or "Remote"
                    else:
                        job_geo = str(job_geo_raw).strip() if job_geo_raw else "Remote"

                    job_level_raw = item.get("jobLevel")
                    if isinstance(job_level_raw, list):
                        job_level = ", ".join(str(x) for x in job_level_raw if str(x).strip()) or "Mid-level"
                    else:
                        job_level = str(job_level_raw).strip() if job_level_raw else "Mid-level"

                    job = JobListingCreate(
                        title=clean_title,
                        company=clean_company,
                        location=job_geo,
                        employment_type=job_type,
                        experience_level=job_level,
                        salary_min=sal_min,
                        salary_max=sal_max,
                        salary_currency=item.get("salaryCurrency") or "USD",
                        description=clean_desc,
                        requirements=clean_reqs,
                        application_url=url,
                        posted_date=pub_date,
                        source=self.name,
                        external_id=str(item.get("id", "")),
                    )
                    results.append(job)
                    if len(results) >= limit:
                        break

        except Exception as e:
            logger.error(f"Error fetching jobs from Jobicy: {e}")
        return results
