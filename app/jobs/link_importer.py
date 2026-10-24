"""Job-Link Import & Assisted Ingestion Utility.

Extracts job vacancy metadata from public URLs (LinkedIn, Internshala, Glassdoor,
Greenhouse, Lever, Ashby, or any employer career page) using OpenGraph,
JSON-LD JobPosting schemas, and semantic HTML parsing.
"""
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
import httpx

from app.core.logging import get_logger
from app.core.security import validate_external_url
from app.core.text_cleaner import clean_html_description
from app.jobs.dedup import normalize_job_url
from app.jobs.schemas import JobListingCreate

logger = get_logger("link_importer")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AIJobAssistant/1.0"


def detect_source_from_url(url: str) -> str:
    """Identify the hosting platform or ATS from the domain name."""
    netloc = urlparse(url).netloc.lower()
    if "linkedin.com" in netloc:
        return "linkedin"
    elif "internshala.com" in netloc:
        return "internshala"
    elif "glassdoor.com" in netloc:
        return "glassdoor"
    elif "greenhouse.io" in netloc:
        return "greenhouse"
    elif "lever.co" in netloc:
        return "lever"
    elif "ashbyhq.com" in netloc:
        return "ashby"
    elif "smartrecruiters.com" in netloc:
        return "smartrecruiters"
    elif "remoteok.com" in netloc:
        return "remoteok"
    elif "jobicy.com" in netloc:
        return "jobicy"
    elif "arbeitnow.com" in netloc:
        return "arbeitnow"
    return "career_page"


def strip_html_tags(html_text: str) -> str:
    """Convert HTML string to clean plain text."""
    return clean_html_description(html_text)


def extract_json_ld_job(html: str) -> Optional[Dict[str, Any]]:
    """Look for schema.org JobPosting in JSON-LD script tags."""
    scripts = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for s in scripts:
        try:
            data = json.loads(s.strip())
            # Can be a single dict or @graph list
            candidates = []
            if isinstance(data, dict):
                if data.get("@type") == "JobPosting":
                    return data
                if "@graph" in data and isinstance(data["@graph"], list):
                    candidates.extend(data["@graph"])
            elif isinstance(data, list):
                candidates.extend(data)

            for item in candidates:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        except Exception:
            continue
    return None


def extract_meta_tags(html: str) -> Dict[str, str]:
    """Extract OpenGraph and standard meta tags from HTML."""
    tags = {}
    for m in re.finditer(r'<meta[^>]+(?:name|property)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE):
        tags[m.group(1).lower()] = m.group(2)
    # Also handle inverted content= then property=
    for m in re.finditer(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:name|property)=["\']([^"\']+)["\']', html, re.IGNORECASE):
        tags[m.group(2).lower()] = m.group(1)
    # Title tag fallback
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        tags["page_title"] = title_match.group(1).strip()
    return tags


async def fetch_and_parse_job_url(
    url: str,
    override_title: Optional[str] = None,
    override_company: Optional[str] = None,
    override_description: Optional[str] = None,
) -> JobListingCreate:
    """Safely fetch job URL, extract structured/OpenGraph metadata, and return normalized listing."""
    safe_url = validate_external_url(url)
    source_name = detect_source_from_url(safe_url)
    norm_url = normalize_job_url(safe_url)

    html = ""
    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(safe_url)
            if resp.status_code == 200:
                html = resp.text[:200000]  # Cap at 200KB for safety
    except Exception as e:
        logger.warning(f"Could not fetch raw HTML for {safe_url}: {e}")

    # 1. Try JSON-LD schema
    json_ld = extract_json_ld_job(html) if html else None
    meta = extract_meta_tags(html) if html else {}

    title = override_title
    company = override_company
    description = override_description
    location = "Remote"

    if json_ld:
        title = title or json_ld.get("title")
        org = json_ld.get("hiringOrganization")
        if isinstance(org, dict):
            company = company or org.get("name")
        elif isinstance(org, str):
            company = company or org

        description = description or strip_html_tags(json_ld.get("description", ""))
        loc_data = json_ld.get("jobLocation")
        if isinstance(loc_data, dict):
            addr = loc_data.get("address")
            if isinstance(addr, dict):
                location = addr.get("addressLocality") or addr.get("addressRegion") or addr.get("addressCountry") or "Remote"

    # 2. Fallback to OpenGraph / Meta tags
    if not title:
        title = meta.get("og:title") or meta.get("twitter:title") or meta.get("page_title") or "Imported Job"
        # Often title is in format: "Job Title at Company" or "Job Title - Company"
        if " at " in title:
            parts = title.split(" at ", 1)
            title = parts[0].strip()
            if not company:
                company = parts[1].split("|")[0].split("-")[0].strip()
        elif " - " in title:
            parts = title.split(" - ", 1)
            title = parts[0].strip()
            if not company:
                company = parts[1].split("|")[0].strip()

    if not company:
        company = meta.get("og:site_name") or urlparse(safe_url).netloc.split(".")[0].capitalize()

    if not description:
        description = meta.get("og:description") or meta.get("description") or f"Imported job posting from {safe_url}"

    return JobListingCreate(
        title=title.strip() if title else "Job Vacancy",
        company=company.strip() if company else "Company",
        location=location,
        employment_type="Full-time",
        experience_level="Mid-level",
        description=strip_html_tags(description) if description else f"Imported job posting from {safe_url}",
        requirements=[],
        application_url=norm_url,
        posted_date=datetime.now(timezone.utc),
        source=source_name,
    )
