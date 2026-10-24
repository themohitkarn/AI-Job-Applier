"""Job deduplication and URL normalization utilities."""
import hashlib
import re
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "msclkid", "mc_eid"
}


def normalize_job_url(url: str) -> str:
    """Strip marketing tracking query parameters and canonicalize URL format."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        # Strip tracking query parameters
        filtered_queries = [
            (k, v) for k, v in parse_qsl(parsed.query)
            if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urlencode(filtered_queries)
        # Normalize path
        normalized_path = parsed.path.rstrip("/")
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.params,
            new_query,
            ""  # drop fragment
        ))
        return normalized
    except Exception:
        return url.strip()


def normalize_text_token(text: str) -> str:
    """Clean text for robust fingerprinting comparison."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    # Remove common company suffixes
    cleaned = re.sub(r"\b(inc|llc|ltd|gmbh|corp|technologies|corporation)\b", "", cleaned)
    tokens = [t for t in cleaned.split() if t]
    return " ".join(tokens)


def compute_job_fingerprint(
    company: str,
    title: str,
    location: Optional[str] = None,
    external_id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    """Calculate a deterministic SHA-256 fingerprint for duplicate detection."""
    norm_comp = normalize_text_token(company)
    norm_title = normalize_text_token(title)
    norm_loc = normalize_text_token(location or "")
    norm_ext = (external_id or "").strip().lower()
    norm_url = normalize_job_url(url or "")

    # If external ID exists, combine with company
    if norm_ext:
        raw_key = f"{norm_comp}|{norm_title}|ext:{norm_ext}"
    elif norm_url:
        raw_key = f"{norm_comp}|{norm_title}|url:{norm_url}"
    else:
        raw_key = f"{norm_comp}|{norm_title}|loc:{norm_loc}"

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
