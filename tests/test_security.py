"""Tests for Security, SSRF, File Validation, and Path Traversal Protection."""
from pathlib import Path
import pytest
from app.core.logging import sanitize_text
from app.core.security import (
    sanitize_filename,
    sanitize_prompt_input,
    validate_external_url,
    validate_file_path,
    validate_file_upload,
)


def test_sanitize_filename():
    """Verify filename sanitization removes path separators and illegal characters."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("my resume (1).pdf") == "my resume 1.pdf"


def test_path_traversal_detection():
    """Verify validate_file_path blocks attempts to escape base directory."""
    base_dir = Path("./data/resumes").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    safe_target = base_dir / "alex_resume.pdf"
    assert validate_file_path(base_dir, safe_target) == safe_target

    dangerous_target = base_dir / "../../app.py"
    with pytest.raises(ValueError, match="Directory traversal detected"):
        validate_file_path(base_dir, dangerous_target)


def test_file_upload_validation():
    """Verify upload extension and size checks."""
    # Disallowed extension
    with pytest.raises(ValueError, match="Invalid file type"):
        validate_file_upload("exploit.exe", 1024)

    # File exceeding limit
    with pytest.raises(ValueError, match="exceeds limit"):
        validate_file_upload("large.pdf", 15 * 1024 * 1024, max_size_mb=10)

    # Empty file
    with pytest.raises(ValueError, match="empty"):
        validate_file_upload("empty.pdf", 0)

    # Valid file
    validate_file_upload("valid_resume.pdf", 50000)


def test_ssrf_url_validation():
    """Verify URL validation rejects unsafe schemes and private addresses."""
    # Disallowed scheme
    with pytest.raises(ValueError, match="Disallowed URL scheme"):
        validate_external_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Disallowed URL scheme"):
        validate_external_url("javascript:alert(1)")

    # Private loopback addresses
    with pytest.raises(ValueError, match="SSRF Protection"):
        validate_external_url("http://127.0.0.1:8000/internal")

    with pytest.raises(ValueError, match="SSRF Protection"):
        validate_external_url("http://localhost:9000/admin")

    with pytest.raises(ValueError, match="SSRF Protection"):
        validate_external_url("http://169.254.169.254/latest/meta-data")

    # Legitimate public URL
    safe_url = validate_external_url("https://jobs.example.com/apply/12345")
    assert safe_url == "https://jobs.example.com/apply/12345"


def test_secret_redaction_in_logging():
    """Verify sensitive tokens and keys are scrubbed from log messages."""
    raw_log = "Connected using key gsk_AbCdEf1234567890XyZ1234567890 and password='super_secret_password'"
    cleaned = sanitize_text(raw_log)
    assert "gsk_AbCdEf1234567890XyZ1234567890" not in cleaned
    assert "[REDACTED_CREDENTIAL]" in cleaned
