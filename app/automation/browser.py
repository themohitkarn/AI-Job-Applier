"""Playwright browser automation service with user approval gates."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.adapters.base import BaseSiteAdapter
from app.automation.adapters.generic import GenericJobAdapter
from app.automation.adapters.greenhouse import GreenhouseAdapter
from app.automation.adapters.lever import LeverAdapter
from app.automation.schemas import ApplicationStatus, BrowserActionRequest, BrowserActionResponse
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import validate_external_url
from app.db.models import Application, ApplicationDraft, JobListing, ResumeDocument, UserProfile

logger = get_logger("browser_automation")


class BrowserAutomationService:
    """Safely automates job form interactions with strict human approval gates."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.generic_adapter = GenericJobAdapter()
        self.adapters = [
            GreenhouseAdapter(),
            LeverAdapter(),
            self.generic_adapter,
        ]

    def _select_adapter(self, url: str) -> BaseSiteAdapter:
        """Choose specialized ATS adapter or generic fallback."""
        for a in self.adapters:
            if a.can_handle(url):
                return a
        return self.generic_adapter

    async def execute_application_flow(self, req: BrowserActionRequest) -> BrowserActionResponse:
        """Run form inspection, mapping, and dry-run/approval submission."""
        # 1. Fetch Job
        stmt_job = select(JobListing).where(JobListing.id == req.job_id)
        job = (await self.db.execute(stmt_job)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job ID {req.job_id} not found.")

        # 2. Fetch User Profile
        stmt_prof = select(UserProfile).order_by(UserProfile.id.asc()).limit(1)
        profile = (await self.db.execute(stmt_prof)).scalar_one_or_none()
        if not profile:
            raise ValueError("User profile not found. Please create a profile first.")

        # 3. Fetch Resume Document
        resume_doc: Optional[ResumeDocument] = None
        if req.resume_id:
            stmt_res = select(ResumeDocument).where(ResumeDocument.id == req.resume_id)
            resume_doc = (await self.db.execute(stmt_res)).scalar_one_or_none()
        if not resume_doc:
            # Fallback to primary or newest
            stmt_res = select(ResumeDocument).where(ResumeDocument.user_id == profile.id).order_by(ResumeDocument.is_primary.desc(), ResumeDocument.id.desc())
            resume_doc = (await self.db.execute(stmt_res)).scalars().first()

        # 4. Fetch Draft
        cover_letter_text: Optional[str] = None
        if req.draft_id:
            stmt_draft = select(ApplicationDraft).where(ApplicationDraft.id == req.draft_id)
            draft = (await self.db.execute(stmt_draft)).scalar_one_or_none()
            if draft:
                cover_letter_text = draft.content

        # 5. Get or Create Application Record
        stmt_app = select(Application).where(Application.job_id == job.id, Application.user_id == profile.id)
        app_record = (await self.db.execute(stmt_app)).scalar_one_or_none()
        if not app_record:
            app_record = Application(
                job_id=job.id,
                user_id=profile.id,
                resume_id=resume_doc.id if resume_doc else None,
                draft_id=req.draft_id,
                status=ApplicationStatus.DISCOVERED.value,
            )
            self.db.add(app_record)
            await self.db.commit()
            await self.db.refresh(app_record)

        # Validate URL
        safe_url = validate_external_url(job.application_url)

        profile_dict = {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone or "",
            "location": profile.location or "",
        }

        screenshot_rel_path: Optional[str] = None
        fields_filled: Dict[str, str] = {}
        error_msg: Optional[str] = None

        # Select appropriate adapter based on destination domain
        adapter = self._select_adapter(safe_url)
        logger.info(f"Using {adapter.__class__.__name__} for {safe_url}")

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=self.settings.browser_headless,
                slow_mo=self.settings.browser_slow_mo_ms,
            )
            context: BrowserContext = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            page: Page = await context.new_page()

            try:
                logger.info(f"Navigating to {safe_url}...")
                app_record.last_step = f"Opening {safe_url}"
                await page.goto(safe_url, timeout=self.settings.browser_timeout_ms, wait_until="domcontentloaded")

                # Fill form fields
                app_record.last_step = "Filling form fields"
                resume_file_path = resume_doc.file_path if resume_doc else None
                fields_filled = await adapter.fill_form(
                    page=page,
                    profile_data=profile_dict,
                    resume_path=resume_file_path,
                    cover_letter=cover_letter_text,
                )

                # Capture diagnostic screenshot
                screenshot_filename = f"app_{app_record.id}_{uuid.uuid4().hex[:6]}.png"
                screenshot_full_path = self.settings.screenshots_dir / screenshot_filename
                await page.screenshot(path=str(screenshot_full_path), full_page=False)
                screenshot_rel_path = str(screenshot_full_path)

                # STRICT USER APPROVAL CHECK
                if req.dry_run or not req.user_confirmed_submission:
                    app_record.status = ApplicationStatus.READY_FOR_APPROVAL.value
                    app_record.requires_approval = True
                    app_record.last_step = "Form pre-filled. Awaiting user approval to submit."
                    await self.db.commit()
                    await browser.close()

                    return BrowserActionResponse(
                        application_id=app_record.id,
                        job_id=job.id,
                        status=ApplicationStatus.READY_FOR_APPROVAL,
                        last_step=app_record.last_step,
                        fields_filled=fields_filled,
                        screenshot_path=screenshot_rel_path,
                        requires_user_approval=True,
                        message="Form pre-filled in dry-run mode. Explicit user confirmation is required before final submission.",
                    )

                # USER APPROVED FINAL SUBMISSION
                app_record.status = ApplicationStatus.SUBMITTING.value
                app_record.is_user_approved = True
                app_record.approved_at = datetime.now(timezone.utc)
                app_record.last_step = "Submitting application form"

                # Look for submit button
                submit_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Apply")',
                ]
                submitted = False
                for sel in submit_selectors:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        submitted = True
                        break

                if not submitted:
                    app_record.status = ApplicationStatus.VERIFICATION_REQUIRED.value
                    app_record.error_message = "Could not locate visible submit button on the application page."
                    await self.db.commit()
                    await browser.close()
                    return BrowserActionResponse(
                        application_id=app_record.id,
                        job_id=job.id,
                        status=ApplicationStatus.VERIFICATION_REQUIRED,
                        last_step="Submit button not found",
                        fields_filled=fields_filled,
                        screenshot_path=screenshot_rel_path,
                        requires_user_approval=False,
                        message="Fields were populated, but no distinct submit button was detected. Please verify manually.",
                    )

                # Wait for response or confirmation
                await page.wait_for_timeout(3000)
                is_confirmed, ref = await adapter.check_submission_confirmation(page)

                if is_confirmed:
                    app_record.status = ApplicationStatus.CONFIRMED.value
                    app_record.submitted_at = datetime.now(timezone.utc)
                    app_record.confirmation_reference = ref or "Confirmed by page response"
                    app_record.last_step = "Application submission confirmed."
                    msg = f"Application successfully submitted! Confirmation: {app_record.confirmation_reference}"
                else:
                    app_record.status = ApplicationStatus.VERIFICATION_REQUIRED.value
                    app_record.submitted_at = datetime.now(timezone.utc)
                    app_record.last_step = "Submitted, but automated confirmation signature could not be verified."
                    msg = "Application submitted, but target page did not show a standard confirmation message. Manual verification recommended."

                # Final screenshot
                final_ss = self.settings.screenshots_dir / f"final_app_{app_record.id}.png"
                await page.screenshot(path=str(final_ss))
                screenshot_rel_path = str(final_ss)

                await self.db.commit()
                await browser.close()

                return BrowserActionResponse(
                    application_id=app_record.id,
                    job_id=job.id,
                    status=ApplicationStatus(app_record.status),
                    last_step=app_record.last_step,
                    fields_filled=fields_filled,
                    screenshot_path=screenshot_rel_path,
                    requires_user_approval=False,
                    confirmation_reference=app_record.confirmation_reference,
                    message=msg,
                )

            except Exception as e:
                logger.error(f"Browser automation error for job {job.id}: {e}")
                app_record.status = ApplicationStatus.FAILED.value
                app_record.error_message = str(e)
                app_record.last_step = f"Encountered error: {e}"

                try:
                    err_ss = self.settings.screenshots_dir / f"error_app_{app_record.id}.png"
                    await page.screenshot(path=str(err_ss))
                    screenshot_rel_path = str(err_ss)
                except Exception:
                    pass

                await self.db.commit()
                await browser.close()

                return BrowserActionResponse(
                    application_id=app_record.id,
                    job_id=job.id,
                    status=ApplicationStatus.FAILED,
                    last_step=app_record.last_step,
                    fields_filled=fields_filled,
                    screenshot_path=screenshot_rel_path,
                    requires_user_approval=False,
                    error_message=str(e),
                    message=f"Browser automation failed: {e}",
                )
