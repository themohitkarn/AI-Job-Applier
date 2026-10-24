"""Greenhouse Job Board Connector (Official employer career board public API)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.jobs.connector_base import BaseJobConnector, SourceCapability
from app.jobs.schemas import JobListingCreate

logger = get_logger("connector_greenhouse")


class GreenhouseConnector(BaseJobConnector):
    """Fetches vacancies from employer career pages hosted on Greenhouse."""

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
    USER_AGENT = "AIJobAssistant/1.0 (Direct Employer Discovery; Contact: support@example.com)"

    @property
    def name(self) -> str:
        return "greenhouse"

    @property
    def display_name(self) -> str:
        return "Greenhouse (Employer Career Boards)"

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
            compliance_policy="Uses official public Greenhouse Job Board API for employers with published career boards.",
            enabled=True,
        )

    def _get_target_boards(self) -> List[str]:
        settings = get_settings()
        boards_str = getattr(settings, "greenhouse_boards", "gitlab,cloudflare")
        return [b.strip() for b in boards_str.split(",") if b.strip()]

    async def check_health(self) -> Dict[str, Any]:
        boards = self._get_target_boards()
        if not boards:
            return {
                "connector": self.name,
                "status": "unconfigured",
                "reachable": True,
                "note": "No employer board tokens configured in GREENHOUSE_BOARDS.",
            }
        test_board = boards[0]
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": self.USER_AGENT}) as client:
                resp = await client.get(f"{self.BASE_URL}/{test_board}/jobs")
                return {
                    "connector": self.name,
                    "status": "healthy" if resp.status_code == 200 else f"http_{resp.status_code}",
                    "reachable": resp.status_code == 200,
                    "active_boards": boards,
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
        boards = self._get_target_boards()
        if not boards:
            return results

        keyword_tokens = [k.lower().strip() for k in (keywords or "").split(",") if k.strip()]

        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": self.USER_AGENT}) as client:
            for board in boards:
                if len(results) >= limit:
                    break
                try:
                    url = f"{self.BASE_URL}/{board}/jobs?content=true"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"Greenhouse board '{board}' returned status {resp.status_code}")
                        continue

                    data = resp.json()
                    jobs_data = data.get("jobs", [])
                    company_name = board.capitalize()

                    for j in jobs_data:
                        title = j.get("title") or ""
                        if not title:
                            continue

                        desc = j.get("content") or ""
                        loc_name = (j.get("location") or {}).get("name") or "Remote"

                        # Filter by keyword if provided
                        combined = f"{title} {desc} {loc_name}".lower()
                        if keyword_tokens and not any(kw in combined for kw in keyword_tokens):
                            continue

                        app_url = j.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{j.get('id')}"

                        job = JobListingCreate(
                            title=title.strip(),
                            company=company_name,
                            location=loc_name,
                            employment_type="Full-time",
                            experience_level="Mid-level",
                            description=desc,
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
                    logger.error(f"Error fetching Greenhouse board '{board}': {e}")

        return results
