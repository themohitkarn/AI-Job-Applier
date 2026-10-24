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
