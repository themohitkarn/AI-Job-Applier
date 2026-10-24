"""Structured Logging and Sanitization Module.

Provides correlation tracking, timestamped logs, component attribution,
and secret/PII masking.
"""
import logging
import re
import sys
from typing import Any, Dict, Optional
from datetime import datetime, timezone


# Sensitive pattern regexes for redaction
SECRET_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_.-]+", re.IGNORECASE),
    re.compile(r"password['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"api[-_]?key['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"secret['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    """Mask credentials and sensitive strings from logs."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_CREDENTIAL]", sanitized)
    return sanitized


class SanitizedFormatter(logging.Formatter):
    """Custom formatter that automatically redacts secrets and formats structured output."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the base message
        orig_msg = record.getMessage()
        sanitized_msg = sanitize_text(orig_msg)

        iso_time = datetime.now(timezone.utc).isoformat()
        component = getattr(record, "component", record.name)
        request_id = getattr(record, "request_id", "-")

        formatted = (
            f"[{iso_time}] [{record.levelname:<8}] [{component}] "
            f"[req:{request_id}] {sanitized_msg}"
        )

        if record.exc_info:
            formatted += "\n" + sanitize_text(self.formatException(record.exc_info))
        return formatted


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure root and application loggers with sanitized output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(SanitizedFormatter())
    root_logger.addHandler(console_handler)

    # Return app-specific logger
    app_logger = logging.getLogger("ai_job_assistant")
    app_logger.setLevel(level.upper())
    return app_logger


def get_logger(component_name: str) -> logging.LoggerAdapter:
    """Get a logger adapter bound to a specific component."""
    base_logger = logging.getLogger(f"ai_job_assistant.{component_name}")
    return logging.LoggerAdapter(base_logger, {"component": component_name})
