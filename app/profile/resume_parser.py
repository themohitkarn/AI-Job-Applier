"""Resume parsing and text extraction utility."""
import io
from pathlib import Path
from typing import Tuple
from pypdf import PdfReader

from app.core.logging import get_logger

logger = get_logger("resume_parser")


def extract_text_from_file(file_path: Path) -> str:
    """Extract plain text from PDF or TXT resume files."""
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        try:
            return file_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as e:
            logger.error(f"Failed to read TXT resume: {e}")
            return ""

    elif suffix == ".pdf":
        try:
            reader = PdfReader(str(file_path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    pages_text.append(extracted.strip())
            return "\n\n".join(pages_text).strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"Could not parse PDF file: {str(e)}")

    else:
        # Fallback reading
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""
