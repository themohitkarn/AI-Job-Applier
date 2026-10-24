"""Safe text and HTML cleaning utilities for job postings."""
import html
import re


def clean_html_description(raw: str) -> str:
    """Safely sanitize, decode, and normalize HTML job descriptions into human-readable plain text.

    Removes script, style, comments, and markup; decodes HTML entities (including double-escaped);
    resolves mojibake and non-breaking spaces; and normalizes whitespace while preserving paragraphs.
    """
    if not raw or not isinstance(raw, str):
        return ""

    # Pass 1: Decode entities in case the markup was stored as &lt;div class=&quot;gmail_default&quot;&gt;
    text = html.unescape(raw)

    # Remove script and style elements completely (including code inside them)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)

    # Convert list elements to readable bullet points
    text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)

    # Convert structural tags to newlines
    text = re.sub(r"<(?:br|p|div|tr|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|tr|h[1-6]|ul|ol|table)>", "\n", text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Pass 2: Decode any entities that were exposed after stripping tags
    text = html.unescape(text)

    # Normalize special whitespace and mojibake
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")  # zero-width space
    text = text.replace("\ufeff", "")  # byte order mark

    # Common mojibake / unicode apostrophes and quotation marks
    text = text.replace("â€™", "'").replace("â€˜", "'")
    text = text.replace("â€œ", '"').replace("â€\x9d", '"').replace("â€", '"')
    text = text.replace("â€“", "-").replace("â€”", "-")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[\x80\x98\x99\x91\x92]", "'", text)
    text = re.sub(r"[\x93\x94]", '"', text)
    text = re.sub(r"[\x96\x97]", "-", text)

    # Normalize whitespace per line and collapse blank lines
    lines = []
    for line in text.splitlines():
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned_line:
            lines.append(cleaned_line)

    return "\n".join(lines).strip()



def safe_parse_list(raw: str | None, default: list | None = None) -> list:
    """Parse a JSON-encoded list or comma-separated string into a Python list.

    Handles both JSON arrays (e.g. '["Python", "FastAPI"]') and plain
    comma-separated strings (e.g. 'Python, FastAPI, SQL') gracefully,
    preventing JSONDecodeError crashes on legacy data.

    Args:
        raw: The raw string to parse (may be None).
        default: Value to return when raw is empty/None.

    Returns:
        A list of strings.
    """
    if default is None:
        default = []
    if not raw or not raw.strip():
        return default
    raw = raw.strip()
    # Try JSON first
    try:
        import json
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        # If JSON parsed to something else (dict, str), treat as single-item
        return [str(parsed)]
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: comma-separated string
    return [item.strip() for item in raw.split(",") if item.strip()]
