"""Specialized form adapter for Lever hosted job application pages."""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from app.automation.adapters.base import BaseSiteAdapter
from app.core.logging import get_logger

logger = get_logger("lever_adapter")


class LeverAdapter(BaseSiteAdapter):
    """Handles Lever application forms (jobs.lever.co)."""

    def can_handle(self, url: str) -> bool:
        return "lever.co" in url.lower()

    async def fill_form(
        self,
        page: Any,
        profile_data: Dict[str, Any],
        resume_path: Optional[str] = None,
        cover_letter: Optional[str] = None,
    ) -> Dict[str, str]:
        filled: Dict[str, str] = {}

        # 1. Full name
        if profile_data.get("full_name"):
            try:
                name_loc = page.locator('input[name="name"]').first
                if await name_loc.is_visible(timeout=1000):
                    await name_loc.fill(profile_data["full_name"])
                    filled["name"] = profile_data["full_name"]
            except Exception:
                pass

        # 2. Email
        if profile_data.get("email"):
            try:
                email_loc = page.locator('input[name="email"]').first
                if await email_loc.is_visible(timeout=1000):
                    await email_loc.fill(profile_data["email"])
                    filled["email"] = profile_data["email"]
            except Exception:
                pass

        # 3. Phone
        if profile_data.get("phone"):
            try:
                phone_loc = page.locator('input[name="phone"]').first
                if await phone_loc.is_visible(timeout=1000):
                    await phone_loc.fill(profile_data["phone"])
                    filled["phone"] = profile_data["phone"]
            except Exception:
                pass

        # 4. Resume upload
        if resume_path and Path(resume_path).exists():
            try:
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(str(resume_path))
                filled["resume"] = Path(resume_path).name
            except Exception as e:
                logger.warning(f"Could not upload resume to Lever form: {e}")

        # 5. Additional Information / Cover Letter
        if cover_letter:
            try:
                comments_loc = page.locator('textarea[name="comments"]').first
                if await comments_loc.is_visible(timeout=1000):
                    await comments_loc.fill(cover_letter)
                    filled["comments"] = "[Cover Letter Filled]"
            except Exception:
                pass

        return filled

    async def check_submission_confirmation(self, page: Any) -> Tuple[bool, Optional[str]]:
        try:
            content = (await page.content()).lower()
            indicators = [
                "application submitted",
                "thank you for applying",
                "thanks for applying",
            ]
            for phrase in indicators:
                if phrase in content:
                    return True, phrase.title()

            heading = await page.locator(".application-confirmation, h1, h2").all_inner_texts()
            for h in heading:
                if any(ind in h.lower() for ind in ["thank you", "thanks", "submitted"]):
                    return True, h.strip()
        except Exception as e:
            logger.warning(f"Error checking Lever confirmation: {e}")

        return False, None
