"""Specialized form adapter for Greenhouse hosted job application boards."""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from app.automation.adapters.base import BaseSiteAdapter
from app.core.logging import get_logger

logger = get_logger("greenhouse_adapter")


class GreenhouseAdapter(BaseSiteAdapter):
    """Handles Greenhouse application forms (boards.greenhouse.io)."""

    def can_handle(self, url: str) -> bool:
        return "greenhouse.io" in url.lower()

    async def fill_form(
        self,
        page: Any,
        profile_data: Dict[str, Any],
        resume_path: Optional[str] = None,
        cover_letter: Optional[str] = None,
    ) -> Dict[str, str]:
        filled: Dict[str, str] = {}
        full_name = profile_data.get("full_name", "")
        parts = full_name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        # 1. First Name / Last Name or Full Name
        try:
            fn_loc = page.locator('#first_name, input[name="first_name"]').first
            if await fn_loc.is_visible(timeout=1000):
                await fn_loc.fill(first_name)
                filled["first_name"] = first_name

            ln_loc = page.locator('#last_name, input[name="last_name"]').first
            if await ln_loc.is_visible(timeout=1000):
                await ln_loc.fill(last_name or first_name)
                filled["last_name"] = last_name or first_name
        except Exception:
            pass

        # 2. Email
        try:
            email_loc = page.locator('#email, input[name="email"]').first
            if await email_loc.is_visible(timeout=1000) and profile_data.get("email"):
                await email_loc.fill(profile_data["email"])
                filled["email"] = profile_data["email"]
        except Exception:
            pass

        # 3. Phone
        try:
            phone_loc = page.locator('#phone, input[name="phone"]').first
            if await phone_loc.is_visible(timeout=1000) and profile_data.get("phone"):
                await phone_loc.fill(profile_data["phone"])
                filled["phone"] = profile_data["phone"]
        except Exception:
            pass

        # 4. Resume upload
        if resume_path and Path(resume_path).exists():
            try:
                # Greenhouse uses file input or data-source="attach"
                file_input = page.locator('input[type="file"][id*="resume" i], input[type="file"]').first
                await file_input.set_input_files(str(resume_path))
                filled["resume"] = Path(resume_path).name
            except Exception as e:
                logger.warning(f"Could not upload resume to Greenhouse form: {e}")

        # 5. Cover letter text
        if cover_letter:
            try:
                cover_loc = page.locator('#cover_letter_text, textarea[name*="cover" i]').first
                if await cover_loc.is_visible(timeout=1000):
                    await cover_loc.fill(cover_letter)
                    filled["cover_letter"] = "[Cover Letter Filled]"
            except Exception:
                pass

        return filled

    async def check_submission_confirmation(self, page: Any) -> Tuple[bool, Optional[str]]:
        try:
            content = (await page.content()).lower()
            indicators = [
                "thank you for applying",
                "application submitted",
                "your application has been received",
            ]
            for phrase in indicators:
                if phrase in content:
                    return True, phrase.title()

            # Check for confirmation header
            heading = await page.locator("h1, h2, #application_confirmation").all_inner_texts()
            for h in heading:
                if any(ind in h.lower() for ind in ["thank you", "received", "submitted"]):
                    return True, h.strip()
        except Exception as e:
            logger.warning(f"Error checking Greenhouse submission confirmation: {e}")

        return False, None
