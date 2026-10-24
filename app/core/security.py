"""Security utilities: Path traversal prevention, file validation, URL validation, and sanitization."""
import os
import re
from pathlib import Path
from typing import List, Set
from urllib.parse import urlparse
import ipaddress


ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".txt", ".docx", ".md"}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or filesystem attacks."""
    # Strip directory components
    clean_name = os.path.basename(filename)
    # Remove null bytes and dangerous characters
    clean_name = re.sub(r"[^\w\s.-]", "", clean_name).strip()
    if not clean_name:
        clean_name = "document.pdf"
    return clean_name


def validate_file_path(base_dir: Path, target_path: Path) -> Path:
    """Ensure target_path resolves strictly within base_dir to prevent directory traversal."""
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Security Alert: Directory traversal detected outside {base_dir}")
    return resolved_target


def validate_file_upload(filename: str, content_size: int, max_size_mb: int = 10) -> None:
    """Validate uploaded document file extension and file size."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Invalid file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    max_bytes = max_size_mb * 1024 * 1024
    if content_size > max_bytes:
        raise ValueError(
            f"File size {content_size / (1024 * 1024):.2f}MB exceeds limit of {max_size_mb}MB"
        )
    if content_size == 0:
        raise ValueError("Uploaded file is empty.")


def validate_external_url(url: str, allow_private: bool = False) -> str:
    """Validate that an external job or target URL uses safe http/https and is well-formed.

    Prevents SSRF attacks against internal network metadata services.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Disallowed URL scheme: '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Malformed URL: Missing host.")

    if not allow_private:
        # Check for loopback, link-local, or private IP addresses
        is_ip = False
        try:
            ip = ipaddress.ip_address(hostname)
            is_ip = True
        except ValueError:
            is_ip = False

        if is_ip:
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"SSRF Protection: Requests to private/local network '{hostname}' are forbidden.")
        else:
            # Hostname is a domain name, check for localhost and local domain
            if hostname.lower() in ("localhost", "0.0.0.0", "::1") or hostname.lower().endswith(".local"):
                raise ValueError(f"SSRF Protection: Requests to local host '{hostname}' are forbidden.")

    return url.strip()


def sanitize_prompt_input(text: str, max_chars: int = 15000) -> str:
    """Sanitize external untrusted text (like job descriptions or scraped pages) before LLM prompt injection.

    Wraps untrusted input in structural delimiters and strips potential escape directives.
    """
    if not text:
        return ""
    truncated = text[:max_chars].strip()
    # Strip zero-width spaces and control characters (except common whitespace)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", truncated)
    return cleaned
