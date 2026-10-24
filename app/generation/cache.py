"""Content generation cache and fingerprinting."""
import hashlib
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("content_cache")


def compute_generation_fingerprint(
    job_id: int,
    profile_hash: str,
    draft_type: str,
    custom_instructions: Optional[str] = None,
    template_version: str = "v1",
) -> str:
    """Compute a deterministic hash for checking cache validity."""
    raw = (
        f"job:{job_id}|prof:{profile_hash}|type:{draft_type}|"
        f"tmpl:{template_version}|inst:{(custom_instructions or '').strip()}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ContentCacheManager:
    """Manages disk-backed caching and invalidation for generated content."""

    def __init__(self):
        self.settings = get_settings()

    def get_cached_file(self, fingerprint: str) -> Optional[str]:
        """Read cached content if file exists on disk."""
        target = self.settings.cache_dir / f"{fingerprint}.txt"
        if target.exists():
            try:
                return target.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Error reading cache file {target}: {e}")
        return None

    def store_cached_file(self, fingerprint: str, content: str) -> Path:
        """Persist generated content in cache directory."""
        target = self.settings.cache_dir / f"{fingerprint}.txt"
        target.write_text(content, encoding="utf-8")
        return target

    def invalidate_cache(self, fingerprint: str) -> bool:
        """Invalidate single cache entry."""
        target = self.settings.cache_dir / f"{fingerprint}.txt"
        if target.exists():
            target.unlink()
            return True
        return False
