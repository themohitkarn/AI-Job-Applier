"""Generic application form adapter using standard semantic heuristics."""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from app.automation.adapters.base import BaseSiteAdapter
from app.core.logging import get_logger

logger = get_logger("generic_adapter")


class GenericJobAdapter(BaseSiteAdapter):
    """Fallback adapter detecting standard HTML form inputs (name, email, phone, resume upload)."""

    def can_handle(self, url: str) -> bool:
        # Generic adapter handles any URL as fallback
        return True

    async def fill_form(
        self,
        page: Any,
        profile_data: Dict[str, Any],
        resume_path: Optional[str] = None,
        cover_letter: Optional[str] = None,
    ) -> Dict[str, str]:
        filled: Dict[str, str] = {}

        # Heuristic field mapping
        field_mappings = [
            ("full_name", profile_data.get("full_name"), [
                'input[name*="name" i]',
                'input[id*="name" i]',
                'input[placeholder*="name" i]',
                'input[autocomplete="name"]',
            ]),
            ("email", profile_data.get("email"), [
                'input[type="email"]',
                'input[name*="email" i]',
                'input[id*="email" i]',
                'input[placeholder*="email" i]',
            ]),
            ("phone", profile_data.get("phone"), [
                'input[type="tel"]',
                'input[name*="phone" i]',
                'input[id*="phone" i]',
                'input[placeholder*="phone" i]',
            ]),
            ("location", profile_data.get("location"), [
                'input[name*="location" i]',
                'input[name*="city" i]',
                'input[placeholder*="location" i]',
            ]),
        ]

        for field_name, value, selectors in field_mappings:
            if not value:
                continue
            for sel in selectors:
                try:
                    locator = page.locator(sel).first
                    if await locator.is_visible(timeout=1000):
                        await locator.fill(str(value))
                        filled[field_name] = str(value)
                        break
                except Exception:
                    continue

        # Fill cover letter if textarea is present
        if cover_letter:
            cover_selectors = [
                'textarea[name*="cover" i]',
                'textarea[id*="cover" i]',
                'textarea[placeholder*="cover" i]',
                'textarea[name*="note" i]',
            ]
            for sel in cover_selectors:
                try:
                    locator = page.locator(sel).first
                    if await locator.is_visible(timeout=1000):
                        await locator.fill(cover_letter)
                        filled["cover_letter"] = "[Cover Letter Filled]"
                        break
                except Exception:
                    continue

        # Upload resume if file input is available
        if resume_path and Path(resume_path).exists():
            file_selectors = [
                'input[type="file"][name*="resume" i]',
                'input[type="file"][id*="resume" i]',
                'input[type="file"][name*="cv" i]',
                'input[type="file"]',
            ]
            for sel in file_selectors:
                try:
                    locator = page.locator(sel).first
                    await locator.set_input_files(str(resume_path))
                    filled["resume"] = Path(resume_path).name
                    break
                except Exception:
                    continue

        return filled

    async def check_submission_confirmation(self, page: Any) -> Tuple[bool, Optional[str]]:
        """Inspect page for legitimate submission indicators."""
        try:
            content = (await page.content()).lower()
            success_indicators = [
                "application submitted",
                "thank you for applying",
                "received your application",
                "application has been sent",
                "we have received your application",
            ]
            for phrase in success_indicators:
                if phrase in content:
                    return True, phrase.title()

            # Check for confirmation elements
            heading = await page.locator("h1, h2, h3").all_inner_texts()
            for h in heading:
                if any(ind in h.lower() for ind in ["thank you", "application received", "success"]):
                    return True, h.strip()

        except Exception as e:
            logger.warning(f"Error checking submission confirmation: {e}")

        return False, None
