"""Job discovery orchestration service."""
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, select, or_, and_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.text_cleaner import clean_html_description
from app.db.models import JobListing, JobMatch, JobSyncRecord
from app.jobs.dedup import compute_job_fingerprint, normalize_job_url
from app.jobs.link_importer import fetch_and_parse_job_url
from app.jobs.registry import get_job_registry
from app.jobs.schemas import JobListingCreate, JobListingFilter

logger = get_logger("job_service")


class JobService:
    """Coordinates job discovery, normalization, deduplication, and database persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.registry = get_job_registry()

    async def save_or_update_job(self, job_data: JobListingCreate) -> Tuple[JobListing, bool]:
        """Deduplicate and insert or update job vacancy record with cleaned descriptions."""
        norm_url = normalize_job_url(job_data.application_url)
        clean_title = clean_html_description(job_data.title)
        clean_company = clean_html_description(job_data.company)
        clean_desc = clean_html_description(job_data.description)

        fingerprint = compute_job_fingerprint(
            company=clean_company,
            title=clean_title,
            location=job_data.location,
            external_id=job_data.external_id,
            url=norm_url,
        )

        stmt = select(JobListing).where(JobListing.fingerprint == fingerprint)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.updated_at = datetime.now(timezone.utc)
            # Ensure existing record descriptions are free of raw HTML tags
            if "<" in existing.description or "&" in existing.description:
                existing.description = clean_html_description(existing.description)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing, False

        new_job = JobListing(
            source=job_data.source,
            external_id=job_data.external_id,
            title=clean_title,
            company=clean_company,
            location=job_data.location,
            employment_type=job_data.employment_type,
            experience_level=job_data.experience_level,
            salary_min=job_data.salary_min,
            salary_max=job_data.salary_max,
            salary_currency=job_data.salary_currency or "USD",
            description=clean_desc,
            requirements=json.dumps(job_data.requirements),
            application_url=norm_url,
            posted_date=job_data.posted_date or datetime.now(timezone.utc),
            deadline=job_data.deadline,
            fingerprint=fingerprint,
            status="active",
        )
        self.db.add(new_job)
        await self.db.commit()
        await self.db.refresh(new_job)
        return new_job, True

    async def clean_stored_descriptions(self) -> int:
        """Scan all stored job listings in database and clean any raw HTML markup."""
        stmt = select(JobListing).where(
            or_(
                JobListing.description.like("%<%"),
                JobListing.description.like("%&%"),
                JobListing.title.like("%<%"),
            )
        )
        result = await self.db.execute(stmt)
        listings = result.scalars().all()
        cleaned_count = 0
        for job in listings:
            cleaned_desc = clean_html_description(job.description)
            cleaned_title = clean_html_description(job.title)
            changed = False
            if cleaned_desc != job.description:
                job.description = cleaned_desc
                changed = True
            if cleaned_title != job.title:
                job.title = cleaned_title
                changed = True
            if changed:
                cleaned_count += 1
        if cleaned_count > 0:
            await self.db.commit()
            logger.info(f"Cleaned raw HTML descriptions for {cleaned_count} existing job records.")
        return cleaned_count

    async def sync_all_enabled_sources(self) -> List[JobSyncRecord]:
        """Fetch and synchronize jobs across all configured and enabled connectors."""
        records: List[JobSyncRecord] = []
        enabled_connectors = self.registry.get_enabled(self.settings.enabled_connectors_list)
        for connector in enabled_connectors:
            rec = await self.sync_connector(connector.name)
            records.append(rec)
        return records

    async def sync_connector(self, connector_name: str) -> JobSyncRecord:
        """Run synchronization for a single named connector."""
        connector = self.registry.get(connector_name)
        if not connector:
            raise ValueError(f"Job connector '{connector_name}' is not registered.")

        sync_rec = JobSyncRecord(
            source=connector.name,
            jobs_fetched=0,
            jobs_parsed=0,
            jobs_rejected=0,
            jobs_duplicate=0,
            jobs_added=0,
            status="RUNNING",
            sync_started_at=datetime.now(timezone.utc),
        )
        self.db.add(sync_rec)
        await self.db.flush()

        try:
            fetched_jobs = await connector.fetch_jobs(
                keywords=self.settings.job_search_keywords,
                location=self.settings.job_search_location,
                limit=self.settings.job_connector_max_results,
            )
            parsed_count = len(fetched_jobs)
            added_count = 0
            duplicate_count = 0

            for job_data in fetched_jobs:
                _, is_new = await self.save_or_update_job(job_data)
                if is_new:
                    added_count += 1
                else:
                    duplicate_count += 1

            sync_rec.jobs_fetched = parsed_count
            sync_rec.jobs_parsed = parsed_count
            sync_rec.jobs_added = added_count
            sync_rec.jobs_duplicate = duplicate_count
            sync_rec.jobs_rejected = 0
            sync_rec.status = "SUCCESS"
            sync_rec.sync_completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info(
                f"Sync complete for {connector.name}: {parsed_count} fetched/parsed, "
                f"{added_count} newly saved, {duplicate_count} duplicate."
            )
            return sync_rec

        except Exception as e:
            await self.db.rollback()
            sync_rec.status = "FAILED"
            sync_rec.error_message = str(e)
            sync_rec.sync_completed_at = datetime.now(timezone.utc)
            self.db.add(sync_rec)
            await self.db.commit()
            logger.error(f"Sync failed for {connector_name}: {e}")
            return sync_rec

    async def import_job_from_url(
        self,
        url: str,
        override_title: Optional[str] = None,
        override_company: Optional[str] = None,
        override_description: Optional[str] = None,
    ) -> Tuple[JobListing, bool]:
        """Import a job directly from a pasted URL (LinkedIn, Internshala, Glassdoor, ATS, or Career page)."""
        parsed_job = await fetch_and_parse_job_url(
            url=url,
            override_title=override_title,
            override_company=override_company,
            override_description=override_description,
        )
        return await self.save_or_update_job(parsed_job)

    async def search_jobs(self, filters: JobListingFilter) -> Tuple[List[JobListing], int]:
        """Search and paginate job vacancies with criteria, work mode, and entry-level sorting."""
        query = select(JobListing).options(selectinload(JobListing.matches))

        if filters.query:
            term = f"%{filters.query}%"
            query = query.where(
                or_(
                    JobListing.title.ilike(term),
                    JobListing.company.ilike(term),
                    JobListing.description.ilike(term),
                )
            )

        if filters.location:
            query = query.where(JobListing.location.ilike(f"%{filters.location}%"))

        if filters.work_mode:
            wm = filters.work_mode.strip().lower()
            if wm == "remote":
                query = query.where(
                    or_(
                        JobListing.location.ilike("%remote%"),
                        JobListing.location.ilike("%anywhere%"),
                        JobListing.location.ilike("%worldwide%"),
                        JobListing.description.ilike("%remote%"),
                        JobListing.description.ilike("%work from home%"),
                        JobListing.description.ilike("%wfh%"),
                    )
                )
            elif wm == "hybrid":
                query = query.where(
                    or_(
                        JobListing.location.ilike("%hybrid%"),
                        JobListing.description.ilike("%hybrid%"),
                    )
                )
            elif wm in ("on-site", "onsite"):
                query = query.where(
                    or_(
                        JobListing.location.ilike("%on-site%"),
                        JobListing.location.ilike("%onsite%"),
                        JobListing.location.ilike("%in-office%"),
                        JobListing.description.ilike("%on-site%"),
                        JobListing.description.ilike("%onsite%"),
                        and_(
                            ~JobListing.location.ilike("%remote%"),
                            ~JobListing.location.ilike("%hybrid%"),
                            JobListing.location != "",
                            JobListing.location.isnot(None),
                        ),
                    )
                )

        if filters.fresher_only:
            query = query.where(
                or_(
                    JobListing.title.ilike("%fresher%"),
                    JobListing.title.ilike("%intern%"),
                    JobListing.title.ilike("%trainee%"),
                    JobListing.title.ilike("%junior%"),
                    JobListing.title.ilike("%graduate%"),
                    JobListing.title.ilike("%entry%"),
                    JobListing.title.ilike("%sde intern%"),
                    JobListing.description.ilike("%fresher%"),
                    JobListing.description.ilike("%internship%"),
                    JobListing.description.ilike("%0-1 year%"),
                    JobListing.description.ilike("%0-2 year%"),
                    JobListing.description.ilike("%no experience%"),
                    JobListing.experience_level.ilike("%entry%"),
                    JobListing.experience_level.ilike("%intern%"),
                )
            )

        if filters.source:
            query = query.where(JobListing.source == filters.source.lower())

        if filters.status:
            query = query.where(JobListing.status == filters.status.lower())

        if filters.min_salary:
            query = query.where(JobListing.salary_max >= filters.min_salary)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Pagination & Sorting
        if filters.sort_by == "fresher_first":
            fresher_order = case(
                (JobListing.title.ilike("%intern%"), 1),
                (JobListing.title.ilike("%fresher%"), 1),
                (JobListing.title.ilike("%trainee%"), 1),
                (JobListing.title.ilike("%graduate%"), 1),
                (JobListing.experience_level.ilike("%intern%"), 1),
                (JobListing.title.ilike("%junior%"), 2),
                (JobListing.title.ilike("%entry%"), 2),
                (JobListing.experience_level.ilike("%entry%"), 2),
                (JobListing.title.ilike("%senior%"), 5),
                (JobListing.title.ilike("%lead%"), 5),
                (JobListing.title.ilike("%principal%"), 5),
                (JobListing.title.ilike("%staff%"), 5),
                (JobListing.title.ilike("%director%"), 5),
                else_=3,
            )
            query = query.order_by(fresher_order.asc(), JobListing.posted_date.desc().nullslast())
        elif filters.sort_by == "relevance":
            relevance_order = case(
                (JobListing.title.ilike("%intern%"), 1),
                (JobListing.title.ilike("%fresher%"), 1),
                (JobListing.title.ilike("%junior%"), 2),
                (JobListing.title.ilike("%entry%"), 2),
                (JobListing.title.ilike("%senior%"), 4),
                (JobListing.title.ilike("%lead%"), 4),
                else_=3,
            )
            query = query.order_by(relevance_order.asc(), JobListing.posted_date.desc().nullslast())
        else:
            query = query.order_by(JobListing.posted_date.desc().nullslast())

        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_job_by_id(self, job_id: int) -> Optional[JobListing]:
        """Retrieve a specific job by database ID."""
        stmt = select(JobListing).where(JobListing.id == job_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def clean_stored_descriptions(self) -> int:
        """Sanitize raw HTML and normalize whitespace across all stored job descriptions in-place."""
        stmt = select(JobListing)
        result = await self.db.execute(stmt)
        jobs = result.scalars().all()
        updated = 0
        for job in jobs:
            if not job.description:
                continue
            cleaned = clean_html_description(job.description)
            if cleaned != job.description:
                job.description = cleaned
                updated += 1
        if updated > 0:
            await self.db.commit()
            logger.info(f"Cleaned {updated} stored job descriptions in-place.")
        return updated
