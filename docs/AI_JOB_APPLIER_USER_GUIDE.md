# AI Auto Job Apply — Complete User & Operations Guide

**Application Path**: `D:\ai-job-assistant`  
**Web Dashboard URL**: `http://127.0.0.1:8000/dashboard`  
**API Documentation**: `http://127.0.0.1:8000/docs`  
**Default AI Engine**: Groq Cloud API with `openai/gpt-oss-120b`

---

## 1. Quick Start Guide

### Prerequisites
- Windows 10/11 or modern Linux/macOS
- Python 3.11.x installed and configured in `.venv`
- A free Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys)

### Launching the Application
Open PowerShell in `D:\ai-job-assistant`:
```powershell
# 1. Activate the Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Launch the FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to:
```
http://127.0.0.1:8000/dashboard
```

---

## 2. Configuring Groq AI (`openai/gpt-oss-120b`) & Resolving 401 Errors

The application uses Groq's high-speed inference engine with `openai/gpt-oss-120b` by default for structured matching, profile intelligence, and cover letter synthesis.

### Setting up `.env`
In the project root `D:\ai-job-assistant\.env`:
```env
AI_PROVIDER="groq"
GROQ_MODEL="openai/gpt-oss-120b"
GROQ_API_KEY="gsk_your_actual_groq_api_key_here"
```

### Live Key Reloading (Zero Downtime)
- You **do not need to restart** the backend when you update your Groq API key in `.env`.
- The configuration loader automatically detects the file's modification timestamp (`st_mtime`) and refreshes settings instantly.
- Any accidental double quotes (`"`) or whitespace pasted around the key are automatically sanitized.

### Understanding the AI Status Badge
In the top-right corner of the dashboard header:
- **Green Badge (`GROQ (openai/gpt-oss-120b) Ready`)**: Groq API key is valid and live inference is active.
- **Red Badge (`GROQ (401 Unauthorized)`)**: Your Groq API key is invalid or expired. An alert banner appears with a direct link to generate a fresh key at `https://console.groq.com/keys`.
- **Yellow / Fallback Mode**: If Groq is temporarily unreachable, the system automatically falls back to deterministic rule-based matching without crashing.

---

## 3. Candidate Profile & AI Profile Intelligence

Navigate to the **Profile & Resumes** tab.

### Core Candidate Profile
Fill in your basic information:
- **Full Name**: Your legal name used on job applications.
- **Email Address**: Valid email for application communications.
- **Years of Experience**: Set to `0.0` or `0.5` if you are a fresher, intern, or career starter.
- **Verified Skills**: Comma-separated technical skills (e.g. `Python, FastAPI, SQL, Docker`).
- **Resume Document Manager**: Upload your PDF or text resume. The system automatically extracts text and makes it available for form filling.

### AI Profile Intelligence & Completeness Audit
Click the **"Run AI Audit"** button:
1. **Completeness Score (0-100%)**: Evaluates whether your profile has all required sections (Headline, Summary, Skills, Target Roles, Education).
2. **Missing Section Alerts**: Pinpoints exactly what is missing and provides tailored advice for entry-level candidates (e.g., adding coursework or academic projects).
3. **Canonical Skill Corrections**:
   - Detects common misspellings and aliases (e.g., `pyhton` -> `Python`, `fast api` -> `FastAPI`, `postgres sql` -> `PostgreSQL`, `dokcer` -> `Docker`).
   - Click the green **"Accept"** button on any suggestion to standardize your profile immediately.
4. **Recommended Skills**:
   - Suggests complementary, in-demand technologies matching your stack (e.g., recommending *Docker*, *SQLAlchemy*, or *PostgreSQL* for Python developers).
   - Click any **"+ Skill"** pill to instantly add it to your verified skills.
5. **Undo / Revert Safety Gate**:
   - Before applying any changes, the system creates an automated snapshot in `profile_snapshots`.
   - If you ever want to roll back, click the **"Undo Last Changes"** button to restore your exact previous profile state.

---

## 4. Job Discovery & Connector Registry

Navigate to the **Connectors & Sources** tab.

### Automated Job Sources
The system queries official public APIs without requiring scrapers or credentials:
- **RemoteOK**: Global remote tech listings.
- **Jobicy**: Remote professional vacancies across tech and product.
- **Arbeitnow**: European and global remote job opportunities.
- **Greenhouse**: Public employer boards (e.g., GitLab, Stripe).
- **Lever**: Public employer boards (e.g., Deliveroo, Spotify).
- **Ashby**: Public employer career postings with detailed descriptions.
- **SmartRecruiters**: Public employer job boards with rich qualifications.

Click **"Trigger Discovery Sync"** in the top navigation bar to fetch new vacancies on demand.

### Compliance-Protected Sources (Assisted Import)
Platforms like **LinkedIn**, **Internshala**, and **Glassdoor** prohibit unauthorized automated scraping. The platform respects their terms by providing an **Assisted Import** workflow:
1. Copy the job vacancy URL from your browser (e.g., from LinkedIn or Internshala).
2. Navigate to **Connectors & Sources** -> **Import Job via URL**.
3. Paste the URL and click **"Import Job"**.
4. The system securely fetches the public page, extracts structured JSON-LD / OpenGraph metadata, sanitizes the description, and stores it in your database.

---

## 5. Fresher-First AI Job Matching

Navigate to the **Jobs & Vacancies** or **Matches & Eligibility** tab.

### How Matching Works
Click **"Match"** on any job card:
1. Hard qualification requirements and experience levels are checked deterministically.
2. **Fresher Prioritization**:
   - Internships, entry-level, graduate, trainee, and junior roles receive a **+15.0 score bonus**.
   - Missing optional/preferred skills does **NOT** disqualify freshers.
   - High-level executive or senior roles (Director, VP, Principal, 5+ years) are marked `NEEDS_REVIEW` or `INELIGIBLE` for freshers to prevent wasted applications.
3. Full job descriptions (up to 3,500 characters) are evaluated by Groq `openai/gpt-oss-120b` against candidate skills and education.
4. **Match Caching**: Results are cached by `job.fingerprint + profile_hash`. Clicking "Match" on a previously evaluated job returns instantly without consuming LLM tokens.

### Understanding Match Badges
- **`STRONG_MATCH` (Green, >= 70%)**: High-probability match with strong skill alignment.
- **`PARTIAL_MATCH` (Blue, 50-69%)**: Good technical foundation with minor skill gaps.
- **`NEEDS_REVIEW` (Yellow)**: Marginal match or high experience requirement.
- **`INELIGIBLE` (Red)**: Hard requirement constraint violated (e.g. 10+ years required for a 0-year candidate).
- **`AI Evaluated` vs `Rule Fallback`**: Transparently informs you whether Groq AI or the rule-based fallback produced the score.
- **`Low-Information Warning`**: Appears on jobs where the listing text was very brief, ensuring you know the assessment is tentative.

---

## 6. Safe Auto-Apply Workflow

Navigate to the **Applications & Approvals** tab.

The platform enforces a strict **Human-in-the-Loop** approval workflow:

### Step 1: Pre-Fill (Dry-Run Mode)
Click **"Prepare Application"** on any eligible job:
1. The system verifies that the job is not marked `INELIGIBLE`.
2. Playwright launches a browser session and navigates to the official application URL.
3. Bot barriers and CAPTCHAs are inspected. If detected, the application transitions to `MANUAL_ACTION_REQUIRED`, captures a screenshot, and informs you to complete the application in your browser.
4. The ATS adapter locates form fields and pre-fills your verified name, email, phone, uploaded resume, and cover letter.
5. A high-resolution screenshot of the filled form is captured and saved in `data/screenshots/`.
6. The process halts immediately before clicking submit, and the application status is set to:
   $$\text{Status} = \mathbf{READY\_FOR\_APPROVAL}$$

### Step 2: Human Review & Approval
1. View the pre-filled fields and diagnostic screenshot in the **Applications & Approvals** tab.
2. If satisfied, click the green **"Approve & Submit"** button.
3. The backend re-launches with explicit authorization (`user_confirmed_submission = True`), locates the submit button, clicks it, and verifies the submission confirmation message.
4. The application transitions to `CONFIRMED` with a recorded confirmation reference.

---

## 7. Troubleshooting & FAQ

| Problem | Cause | Solution |
|:---|:---|:---|
| **AI Status Badge is Red (`401 Unauthorized`)** | Stale or invalid `GROQ_API_KEY` in `.env`. | Open `.env`, paste a valid key from [Groq Console](https://console.groq.com/keys), save the file. The dashboard will reload the key automatically. |
| **Playwright fails to launch browser** | Missing Playwright Chromium binaries on new installation. | Run `.\.venv\Scripts\python.exe -m playwright install chromium` in PowerShell. |
| **Job Description looks like raw HTML** | Legacy data ingested prior to text sanitizer deployment. | Ingested jobs are now automatically sanitized. For legacy listings, re-fetch via **Trigger Discovery Sync**. |
| **Application shows `MANUAL_ACTION_REQUIRED`** | Target website employs Cloudflare Turnstile, reCAPTCHA, or custom login gates. | Open the original application link in your personal browser and complete the final submission directly. |
| **Accidentally accepted an unwanted skill suggestion** | User accepted a normalization proposal. | Click **"Undo Last Changes"** in the Profile Intelligence card to restore previous state immediately. |
