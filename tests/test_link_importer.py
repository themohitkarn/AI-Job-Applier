"""Tests for Job-Link Importer and Metadata Extraction."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.jobs.link_importer import (
    detect_source_from_url,
    extract_json_ld_job,
    extract_meta_tags,
    fetch_and_parse_job_url,
    strip_html_tags,
)


def test_detect_source_from_url():
    """Verify source classification based on destination URL."""
    assert detect_source_from_url("https://www.linkedin.com/jobs/view/123456789") == "linkedin"
    assert detect_source_from_url("https://internshala.com/internship/detail/python-internship") == "internshala"
    assert detect_source_from_url("https://www.glassdoor.com/job-listing/senior-developer-jl.htm") == "glassdoor"
    assert detect_source_from_url("https://boards.greenhouse.io/stripe/jobs/45678") == "greenhouse"
    assert detect_source_from_url("https://jobs.lever.co/spotify/abcdef") == "lever"
    assert detect_source_from_url("https://jobs.ashbyhq.com/scale/12345") == "ashby"
    assert detect_source_from_url("https://jobs.smartrecruiters.com/company/999") == "smartrecruiters"
    assert detect_source_from_url("https://careers.google.com/jobs/results/111") == "career_page"


def test_strip_html_tags():
    """Verify HTML tags and entities are cleaned into readable plain text."""
    raw = "<p>Join our team!<br>We need <strong>Python</strong> &amp; FastAPI skills.</p>"
    cleaned = strip_html_tags(raw)
    assert "Join our team!" in cleaned
    assert "<strong>" not in cleaned
    assert "Python & FastAPI" in cleaned


def test_extract_json_ld_job():
    """Verify JSON-LD JobPosting schema extraction."""
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org/",
          "@type": "JobPosting",
          "title": "Lead Software Architect",
          "description": "<p>Lead our engineering team.</p>",
          "hiringOrganization": {
            "@type": "Organization",
            "name": "Acme Global"
          },
          "jobLocation": {
            "@type": "Place",
            "address": {
              "addressLocality": "San Francisco"
            }
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    job = extract_json_ld_job(html)
    assert job is not None
    assert job["title"] == "Lead Software Architect"
    assert job["hiringOrganization"]["name"] == "Acme Global"


def test_extract_meta_tags():
    """Verify OpenGraph and fallback meta tag extraction."""
    html = """
    <html>
      <head>
        <meta property="og:title" content="Backend Engineer at Horizon Labs" />
        <meta property="og:description" content="Build event-driven microservices." />
        <meta property="og:site_name" content="Horizon Labs" />
        <title>Backend Engineer - Careers</title>
      </head>
      <body></body>
    </html>
    """
    meta = extract_meta_tags(html)
    assert meta["og:title"] == "Backend Engineer at Horizon Labs"
    assert meta["og:site_name"] == "Horizon Labs"
    assert meta["page_title"] == "Backend Engineer - Careers"


@pytest.mark.asyncio
async def test_fetch_and_parse_job_url_mock():
    """Verify end-to-end link parsing with mock HTTP response."""
    sample_html = """
    <html>
      <head>
        <meta property="og:title" content="Senior AI Engineer at Neural Dynamics" />
        <meta property="og:description" content="Design and deploy agentic AI pipelines." />
        <meta property="og:site_name" content="Neural Dynamics" />
      </head>
      <body></body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        job = await fetch_and_parse_job_url("https://jobs.example.com/view/777")
        assert job.title == "Senior AI Engineer"
        assert job.company == "Neural Dynamics"
        assert job.source == "career_page"
        assert "agentic AI pipelines" in job.description
