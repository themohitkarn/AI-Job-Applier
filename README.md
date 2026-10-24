# AI Auto Job Apply — Multi-Source Job Discovery & Application Platform

A modular, production-ready, AI-powered platform for discovering tech jobs across public APIs and employer ATS career boards, importing vacancies from major portals, transparently evaluating candidate eligibility, generating tailored application materials, and safely automating job application forms with strict human-in-the-loop approval gates.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   Interactive Web UI &      |
                      |   FastAPI REST API (/v1)    |
                      +--------------+--------------+
                                     |
    +--------------------------------+--------------------------------+
    |                                |                                |
+---+--------------------+  +--------+-----------+  +-----------------+---+
|  AI Provider Engine    |  |  Multi-Source Job |  | Form Automation     |
|  - Groq (Default)      |  |  Discovery Engine  |  |  - Playwright       |
|  - Ollama (Local)      |  |  - Public APIs     |  |  - ATS Adapters     |
|  - Provider Fallback   |  |  - Employer ATS    |  |    (Greenhouse/Lever|
|                        |  |  - Assisted Import |  |  - Human Approval   |
+---+--------------------+  +--------+-----------+  +-----------------+---+
    |                                |                                |
+---+--------------------+  +--------+-----------+  +-----------------+---+
| Content Generation     |  | Transparent Match  |  | Background Worker   |
| - Cover Letters        |  | - Deterministic    |  | - Periodic Sync     |
| - Cold Emails          |  | - Explainable AI   |  | - Cache Cleanup     |
| - SHA-256 Caching      |  | - Scoring Weights  |  | - Async Scheduler   |
+---+--------------------+  +--------+-----------+  +-----------------+---+
    |                                |                                |
    +--------------------------------+--------------------------------+
                                     |
                      +--------------+--------------+
                      | SQLite Async Persistence    |
                      | SQLAlchemy 2.0 + aiosqlite  |
                      +-----------------------------+
```

---

## 2. Source Capability & Legal Compliance Matrix

Discovery is strictly decoupled from application submission. To ensure 100% legal compliance and respect website terms:
- **Public & Employer APIs**: Used for automated background fetching where official endpoints are published.
- **Portals with Anti-Scraping Terms (LinkedIn, Internshala, Glassdoor)**: Direct automated scraping is **strictly disabled**. Supported through **Assisted Job-Link Import**, where the candidate supplies the specific vacancy link, and our system extracts OpenGraph / JSON-LD preview metadata without violating terms.

| Source | Category | Auto Job Fetching | Link Import | Open Apply Link | Form Pre-Fill | Doc Upload | Confirm Check | Requires Credentials | Compliance & Legal Policy |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Remote OK** | Public API | Yes | Yes | Yes | Yes | Yes | Yes | No | Public JSON feed under standard attribution. Respects rate limits. |
| **Jobicy** | Public API | Yes | Yes | Yes | Yes | Yes | Yes | No | Documented public v2 API within query parameters and pagination limits. |
| **Arbeitnow** | Public API | Yes | Yes | Yes | Yes | Yes | Yes | No | Documented public tech job board API with user-agent attribution. |
| **Greenhouse** | Employer ATS | Yes | Yes | Yes | Yes | Yes | Yes | No | Official public Job Board API for employers with published career boards (`GREENHOUSE_BOARDS`). |
| **Lever** | Employer ATS | Yes | Yes | Yes | Yes | Yes | Yes | No | Official public Postings API for employers with published listings (`LEVER_COMPANIES`). |
| **Ashby** | Employer ATS | Yes | Yes | Yes | Yes | Yes | Yes | No | Official public Job Board API for employers hosted on Ashby (`ASHBY_ORGANIZATIONS`). |
| **SmartRecruiters** | Employer ATS | Yes | Yes | Yes | Yes | Yes | Yes | No | Official public Postings API for employers hosted on SmartRecruiters (`SMARTRECRUITERS_COMPANIES`). |
| **LinkedIn** | Assisted Import | No (ToS prohibited) | Yes | Yes | Yes | Yes | Yes | No | LinkedIn Section 8.2 & robots.txt prohibit bulk scraping. Supported via direct user Job-Link Import. |
| **Internshala** | Assisted Import | No (ToS prohibited) | Yes | Yes | Yes | Yes | Yes | No | Terms of Use prohibit automated scraping/crawling. Supported via direct user Job-Link Import. |
| **Glassdoor** | Assisted Import | No (ToS prohibited) | Yes | Yes | Yes | Yes | Yes | No | Terms of Use & robots.txt prohibit automated extraction. Supported via direct user Job-Link Import. |
| **Employer Pages** | Career Page | No (Varied) | Yes | Yes | Yes | Yes | Yes | No | User-supplied career page URLs parsed via OpenGraph / JSON-LD schemas. |

---

## 3. Quickstart & Installation (Windows 11 / Python 3.11)

### Prerequisites:
- Python 3.11 installed (verified at `C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe` or on system PATH).

### Step 1: Navigate to Project Directory
```powershell
cd d:\ai-job-assistant
```

### Step 2: Activate or Initialize Virtual Environment (`.venv`)
```powershell
# Using Python 3.11
python -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 4: Install Playwright Browser Binaries
Playwright requires Chromium for form automation (approximately 190 MB disk space):
```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

### Step 5: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your credentials and employer target boards are configured:
```ini
AI_PROVIDER="groq"
GROQ_API_KEY="gsk_your_actual_groq_api_key_here"
GROQ_MODEL="openai/gpt-oss-120b"

# Enabled connectors
ENABLED_CONNECTORS="remoteok,jobicy,arbeitnow,greenhouse"

# Configure target employer boards
GREENHOUSE_BOARDS="gitlab,cloudflare"
LEVER_COMPANIES="deliveroo"
ASHBY_ORGANIZATIONS=""
SMARTRECRUITERS_COMPANIES=""
```

---

## 4. Running the Platform

### Start the FastAPI Application & Dashboard
```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Operations Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Sources & Capabilities Matrix**: [http://127.0.0.1:8000/api/v1/jobs/sources](http://127.0.0.1:8000/api/v1/jobs/sources)
- **OpenAPI / Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Start the Preserved Streamlit Outreach Tool (Optional)
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

---

## 5. Job Discovery & Import Workflows

### 1. Automated Discovery (Public APIs & Employer ATS Boards)
Click **Sync Jobs** on the dashboard or invoke:
```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/api/v1/jobs/sync
```
Jobs from RemoteOK, Jobicy, Arbeitnow, and configured employer Greenhouse/Lever/Ashby/SmartRecruiters boards are automatically fetched, normalized, deduplicated, and stored.

### 2. Assisted Job-Link Import (LinkedIn, Internshala, Glassdoor, Career Pages)
Paste any specific vacancy link into the dashboard or invoke:
```powershell
$body = @{ url = "https://www.linkedin.com/jobs/view/1234567890" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/api/v1/jobs/import -ContentType "application/json" -Body $body
```
The link importer extracts OpenGraph/JSON-LD metadata, records source attribution (`linkedin`, `internshala`, etc.), calculates the SHA-256 fingerprint, and readies the vacancy for matching, drafting, and assisted application.

---

## 5. Fresher-Friendly Job Search & Configurable Taxonomy

The platform features an advanced, fresher-first job discovery and transparent matching system:

### 1. Worldwide Search & Work Modes
- **Unrestricted Worldwide Search**: By default, `JOB_SEARCH_LOCATION=""` searches globally across all locations without artificial geo-restrictions.
- **Work Mode Classification**: Jobs are automatically tagged and filterable by `Remote`, `Hybrid`, and `On-site` work modes.

### 2. Five Core Skill & Job Title Groups
Configured centrally via `app/core/keywords.py` and editable via `.env` (`KEYWORD_GROUPS_JSON`):
1. **AI and Machine Learning**: AI Engineer, GenAI Developer, LLM Application Developer, Agentic AI, Multi-Agent Systems, NLP Engineer, Deep Learning Engineer, RAG Developer, Prompt Engineering, ML Intern, AI Automation.
2. **Python and Backend**: Python Developer, Junior Python Developer, Backend Developer, FastAPI Developer, API Developer, Software Developer, Automation Developer.
3. **Web and Full Stack**: Web Developer, Full-Stack Developer, PHP Developer, Laravel Developer, Node.js Developer, JavaScript Developer, HTML, CSS, Bootstrap, Tailwind CSS, Frontend Developer.
4. **Software Engineering**: Software Engineer, Software Development Engineer (SDE), SDE Intern, Graduate Software Engineer, Junior Software Engineer, Software Trainee, Graduate Engineer Trainee, Technical Intern.
5. **Database and Data**: SQL Developer, MySQL Developer, SQLite, DBMS, Database Developer, Junior Data Analyst, Python Data Intern, Data Engineering Intern.

### 3. Technical Synonym & Transferable Skills Mapping
Recognizes foundational and transferable technical competencies across full job descriptions (e.g. `FastAPI` matches `Python` & `API`; `MySQL`/`SQLite` matches `SQL` & `DBMS`; `GenAI`/`LLM` matches `AI` & `Prompt Engineering`).

### 4. Fresher Priority & Honest Matching
- Candidates with zero professional experience are prioritized for internships, trainee programs, graduate roles, and entry-level postings with no experience penalty (`exp_score = 100.0` + configurable `FRESHER_BONUS_SCORE`).
- If a posting requires 10 skills and the candidate possesses 2 core skills in a fresher-friendly role, the job is **not discarded**; it is evaluated honestly as a `PARTIAL_MATCH`.
- Missing preferred or nice-to-have qualifications **never** triggers `INELIGIBLE`.

### 5. Eligibility Result Categories
- **STRONG_MATCH**: Comprehensive qualification alignment with core skills and experience/fresher criteria met.
- **PARTIAL_MATCH**: Solid technical foundation in key skills with room for on-the-job training.
- **NEEDS_REVIEW**: Ambiguous requirements or marginal qualifications requiring manual recruiter/applicant inspection.
- **INELIGIBLE**: Verified mandatory blockers (e.g. strict 5+ years experience required for senior roles when candidate is an entry-level applicant).

---

## 6. Assisted Job-Link Import

### Groq Configuration (Default)
In `.env`:
```ini
AI_PROVIDER="groq"
GROQ_API_KEY="gsk_..."
GROQ_MODEL="openai/gpt-oss-120b"
```

### Ollama Configuration (Optional Local Model)
```ini
AI_PROVIDER="ollama"
OLLAMA_BASE_URL="http://127.0.0.1:11434"
OLLAMA_MODEL="llama3.2"
```

---

## 7. Security and Privacy

- **Zero Hardcoded Secrets**: Credentials remain in `.env`.
- **SSRF Prevention**: All external URLs pass through `validate_external_url`, rejecting loopback, local network, and cloud metadata IP ranges (`127.0.0.1`, `localhost`, `169.254.169.254`).
- **Path Traversal Protection**: Uploaded files and disk caches are strictly bounded by `validate_file_path`.
- **Secret Redaction**: Automated logging filters mask `gsk_...` keys, tokens, and passwords.
- **Mandatory Human Approval**: Automation pauses at `READY_FOR_APPROVAL`. Forms are filled in dry-run mode and are never submitted without explicit user authorization (`user_confirmed_submission=True`).

---

## 8. Testing & Quality Assurance

Run the comprehensive unit and integration test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

All 60 unit and integration tests execute with 100% pass rate.
