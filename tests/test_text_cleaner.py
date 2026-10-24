"""Tests for safe HTML cleaning and text sanitization in job descriptions."""
from app.core.text_cleaner import clean_html_description


def test_clean_html_with_gmail_default_div():
    """Verify that malformed <div class="gmail_default"> is safely converted to clean plain text."""
    raw = '<div class="gmail_default">Looking for a Python Developer with FastAPI experience.</div>'
    cleaned = clean_html_description(raw)
    assert cleaned == "Looking for a Python Developer with FastAPI experience."
    assert "<div" not in cleaned
    assert "gmail_default" not in cleaned


def test_clean_html_with_encoded_entities():
    """Verify that encoded &lt;div class=&quot;gmail_default&quot;&gt; is decoded and stripped."""
    raw = '&lt;div class=&quot;gmail_default&quot;&gt;Looking for a Junior Python Developer.&lt;/div&gt;'
    cleaned = clean_html_description(raw)
    assert cleaned == "Looking for a Junior Python Developer."
    assert "&lt;" not in cleaned
    assert "&quot;" not in cleaned
    assert "gmail_default" not in cleaned


def test_clean_html_removes_scripts_and_styles():
    """Verify script and style blocks including their contents are completely eliminated."""
    raw = '''
    <style>.gmail_default { color: red; }</style>
    <div class="gmail_default">
        <h3>Role Overview</h3>
        <p>Seeking an entry-level engineer.<script>alert("xss")</script></p>
    </div>
    '''
    cleaned = clean_html_description(raw)
    assert "Role Overview" in cleaned
    assert "Seeking an entry-level engineer." in cleaned
    assert "alert" not in cleaned
    assert "color: red" not in cleaned
    assert "<style" not in cleaned
    assert "<script" not in cleaned


def test_clean_html_converts_lists_to_bullets():
    """Verify <li> lists are converted to readable bullet characters."""
    raw = '<p>Key Requirements:</p><ul><li>Python 3.11</li><li>FastAPI</li><li>PostgreSQL</li></ul>'
    cleaned = clean_html_description(raw)
    assert "Key Requirements:" in cleaned
    assert "• Python 3.11" in cleaned
    assert "• FastAPI" in cleaned
    assert "• PostgreSQL" in cleaned
    assert "<ul>" not in cleaned
    assert "<li>" not in cleaned



def test_safe_parse_list_with_json_and_csv():
    """Bug 8 Regression Test: safe_parse_list parses JSON arrays, CSV strings, and empty values gracefully."""
    from app.core.text_cleaner import safe_parse_list

    # Valid JSON array
    assert safe_parse_list('["Python", "FastAPI", "SQL"]') == ["Python", "FastAPI", "SQL"]

    # Plain comma-separated string
    assert safe_parse_list("Python, FastAPI, SQL, Docker") == ["Python", "FastAPI", "SQL", "Docker"]

    # Empty / None / whitespace
    assert safe_parse_list(None) == []
    assert safe_parse_list("") == []
    assert safe_parse_list("   ") == []

    # Single string element in JSON
    assert safe_parse_list('"Python"') == ["Python"]
