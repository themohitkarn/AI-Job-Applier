# AI Auto Job Apply — System Architecture & Design Specification

**Target System**: `D:\ai-job-assistant`  
**Technology Stack**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async/SQLite), Groq Cloud API (`openai/gpt-oss-120b`), Playwright, Tailwind CSS.  
**Specification Version**: 2.2.0  
**Status**: Fully Implemented & Verified (101 Passing Tests)

---

## 1. System Overview & Component Topology

AI Auto Job Apply is a configurable, privacy-first, fresher-friendly job discovery and application platform. The platform coordinates automated job ingestion, semantic candidate eligibility matching, AI-assisted profile enhancement, and automated ATS form pre-filling with strict human approval gates.

```mermaid
flowchart TD
    subgraph UI_Layer ["Presentation & UI Layer"]
        DASH["FastAPI HTML Dashboard (app/web/dashboard.py)"]
        SWAGGER["FastAPI Interactive Docs (/docs, /redoc)"]
    end

    subgraph API_Gateway ["REST API Router Layer (app/api/v1)"]
        R_HEALTH["Health & Config Endpoints"]
        R_JOBS["Jobs & Ingestion Endpoints"]
        R_SOURCES["Connectors & Link Import Endpoints"]
        R_MATCH["Matching & Eligibility Endpoints"]
        R_PROF["Profile & Intelligence Endpoints"]
        R_APPLY["Applications & Approvals Endpoints"]
    end

    subgraph Core_Services ["Application Core Services"]
        JOB_SVC["JobService (app/jobs/service.py)"]
        MATCH_ENG["MatchingEngine (app/matching/engine.py)"]
        PROF_INTEL["ProfileIntelligenceService (app/profile/intelligence.py)"]
        AUTO_SVC["BrowserAutomationService (app/automation/browser.py)"]
        GEN_SVC["GenerationService (app/generation/service.py)"]
        SCHED["SchedulerManager (app/scheduler/manager.py)"]
    end

    subgraph Provider_Layer ["AI & Ingestion Adapters"]
        AI_FAC["AIFactory (app/ai/factory.py)"]
        GROQ_PROV["GroqProvider: openai/gpt-oss-120b"]
        OLLAMA_PROV["OllamaProvider (Optional Local)"]
        CONN_REG["ConnectorRegistry (app/jobs/registry.py)"]
        ATS_ADAPT["ATS Site Adapters (Greenhouse, Lever, Generic)"]
    end

    subgraph Persistence ["Persistence & Storage Layer"]
        SQLITE[("Async SQLite: data/job_assistant.db")]
        CACHE["Cache Directory: data/cache/"]
        SCREENSHOTS["Screenshots Directory: data/screenshots/"]
        RESUMES["Resumes Directory: data/resumes/"]
    end

    DASH --> API_Gateway
    SWAGGER --> API_Gateway
    API_Gateway --> Core_Services
    Core_Services --> Provider_Layer
    Core_Services --> Persistence
    Provider_Layer --> Persistence
```

---

## 2. Ingestion & Connector Registry Architecture

The job discovery subsystem employs a modular plugin pattern with a centralized `ConnectorRegistry`. Sources are classified into **Automated Discovery** and **User-Assisted Import** based on compliance boundaries.

```mermaid
flowchart LR
    subgraph Automated_Sources ["Automated Discovery (Public APIs & ATS)"]
        C1["RemoteOK Connector"]
        C2["Jobicy Connector"]
        C3["Arbeitnow Connector"]
        C4["Greenhouse Board API"]
        C5["Lever Postings API"]
        C6["Ashby Job Board API"]
        C7["SmartRecruiters API"]
    end

    subgraph Assisted_Sources ["User-Assisted Import (Compliance Protected)"]
        L1["LinkedIn Import"]
        L2["Internshala Import"]
        L3["Glassdoor Import"]
    end

    subgraph Ingestion_Pipeline ["Normalization & Deduplication"]
        REG["Connector Registry"]
        TEXT["Text Cleaner & HTML Sanitizer"]
        FINGERPRINT["SHA-256 Fingerprint Generator"]
        DEDUP{"Exists in DB?"}
        DB[("job_listings Table")]
    end

    Automated_Sources --> REG
    Assisted_Sources -->|JSON-LD / Meta Tags| REG
    REG --> TEXT
    TEXT --> FINGERPRINT
    FINGERPRINT --> DEDUP
    DEDUP -->|No| DB
    DEDUP -->|Yes| SKIP["Skip Duplicate (Record Metric)"]
```

### Invariant Deduplication Strategy
To guarantee duplicate immunity across runs and pagination:
$$\text{fingerprint} = \text{SHA256}\left(\text{normalized\_url} \parallel \text{normalized\_title} \parallel \text{normalized\_company}\right)$$
- URLs are canonicalized by removing tracking parameters (`utm_*`, `ref`, `source`, `fbclid`).
- Company and job title strings are lower-cased and whitespace-trimmed.

---

## 3. AI Matching & Eligibility State Machine

Candidate matching uses a two-phase architecture:
1. **Deterministic Baseline**: Evaluates hard constraints (fresher-friendliness, minimum experience years, technical taxonomy synonyms).
2. **AI Semantic Assessment**: Groq (`openai/gpt-oss-120b`) evaluates candidate profile context against the complete job description, returning structured JSON with transparent rationale and skill gaps.

```mermaid
stateDiagram-v2
    [*] --> Ingested: Job Ingested
    Ingested --> CheckCache: Trigger Evaluation
    
    CheckCache --> CachedResult: Cache Hit (job_fp + profile_hash)
    CheckCache --> EvaluateBaseline: Cache Miss

    state EvaluateBaseline {
        [*] --> CheckFresher: Inspect Title & Level
        CheckFresher --> MatchSynonyms: Technical Synonym Matching
        MatchSynonyms --> ScoreExperience: Experience vs Requirement
    }

    EvaluateBaseline --> CallGroqAI: Try AI Evaluation
    CallGroqAI --> AIRecord: Success (is_fallback=False)
    CallGroqAI --> RuleFallback: Error / Timeout (is_fallback=True)

    AIRecord --> PersistMatch: Store in job_matches
    RuleFallback --> PersistMatch: Store in job_matches
    CachedResult --> [*]
    PersistMatch --> Categorized

    state Categorized {
        STRONG_MATCH: Strong Match (Score >= 70%)
        PARTIAL_MATCH: Partial Match (Score >= 50%)
        NEEDS_REVIEW: Needs Review (Marginal)
        INELIGIBLE: Ineligible (Hard constraint failed)
    }
```

### Fresher-First Optimization Rules
- Jobs with "Junior", "Fresher", "Intern", "Trainee", "Entry-level", or 0-1 years required automatically receive an eligibility bonus (+15.0 pts).
- Freshers with 0 professional experience are never marked `INELIGIBLE` solely because preferred/optional qualifications are missing.
- Senior roles (Director, VP, Principal, Staff, 5+ years) are demoted to `NEEDS_REVIEW` or `INELIGIBLE` for fresher candidates, preventing wasted applications.

---

## 4. AI-Assisted Profile Intelligence Architecture

The Profile Intelligence subsystem assists users in standardizing technical terminology, diagnosing missing profile sections, and receiving skill recommendations—all protected by a non-destructive undo/revert workflow.

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate
    participant UI as Dashboard UI
    participant API as /api/v1/profile
    participant Intel as ProfileIntelligenceService
    participant Groq as Groq (openai/gpt-oss-120b)
    participant DB as SQLite Database

    User->>UI: Clicks "Run AI Audit"
    UI->>API: GET /api/v1/profile/audit?use_ai=true
    API->>Intel: audit_profile(profile)
    Intel->>Intel: Calculate completeness score (0-100)
    Intel->>Intel: Deterministic typo lookup (CANONICAL_SKILL_MAP)
    Intel->>Groq: Generate complementary skills & roles
    Groq-->>Intel: Return structured JSON suggestions
    Intel-->>API: ProfileAuditReport
    API-->>UI: Display Score, Suggestions, Add Pills

    User->>UI: Accepts "pyhton" -> "Python" or "+ Add Docker"
    UI->>API: POST /api/v1/profile/apply-suggestions
    API->>Intel: apply_approved_suggestions(profile, req)
    Intel->>DB: Save Snapshot in profile_snapshots table
    Intel->>DB: Update user_profiles (skills, roles, headline)
    DB-->>API: Updated Profile
    API-->>UI: Update UI state (can_undo = True)

    opt User Reverts Changes
        User->>UI: Clicks "Undo Last Changes"
        UI->>API: POST /api/v1/profile/revert
        API->>Intel: revert_last_snapshot(profile)
        Intel->>DB: Restore profile state from snapshot_data
        Intel->>DB: Delete consumed snapshot
        DB-->>API: Restored Profile
        API-->>UI: UI rolled back cleanly
    end
```

---

## 5. Auto-Apply Lifecycle & Human Approval Gate Flow

The browser automation subsystem is built on Playwright with strict human approval gates. Automated submission without explicit human consent is architecturally prevented.

```mermaid
flowchart TD
    START(["Start Application Flow"]) --> ELIG_CHECK{"Pre-Check: Is Job Evaluated INELIGIBLE?"}
    ELIG_CHECK -->|Yes & No Override| BLOCK["Safety Block: ValueError (Cannot apply to ineligible role)"]
    ELIG_CHECK -->|Eligible or Explicitly Confirmed| OPEN_BROWSER["Launch Playwright (Headless/Visible)"]

    OPEN_BROWSER --> NAVIGATE["Navigate to Job Application URL"]
    NAVIGATE --> DETECT_BOT{"CAPTCHA or Cloudflare Detected?"}

    DETECT_BOT -->|Yes| FLAG_MANUAL["Capture Screenshot -> Set Status: MANUAL_ACTION_REQUIRED"]
    FLAG_MANUAL --> ALERT_USER["Alert User to Complete Form Manually"]

    DETECT_BOT -->|No| ADAPTER_SELECT["Select ATS Adapter (Greenhouse, Lever, Generic)"]
    ADAPTER_SELECT --> FILL_FIELDS["Pre-fill Name, Email, Phone, Resume, Cover Letter"]
    FILL_FIELDS --> CAPTURE_SS["Capture Diagnostic Pre-fill Screenshot"]

    CAPTURE_SS --> APPROVAL_GATE{"Is dry_run=True OR user_confirmed_submission=False?"}

    APPROVAL_GATE -->|Yes| HOLD_APPROVAL["Save Status: READY_FOR_APPROVAL<br>Close Browser Session"]
    HOLD_APPROVAL --> AWAIT_HUMAN["Human inspects fields & screenshot in Dashboard"]

    AWAIT_HUMAN --> HUMAN_APPROVES{"User clicks 'Approve & Submit'?"}
    HUMAN_APPROVES -->|No| ABORT["Application remains in READY_FOR_APPROVAL"]
    HUMAN_APPROVES -->|Yes: user_confirmed_submission=True| RE_LAUNCH["Re-launch browser with submission authorization"]

    APPROVAL_GATE -->|No: Explicit Confirmation Authorized| CLICK_SUBMIT["Locate & Click Submit Button"]
    RE_LAUNCH --> CLICK_SUBMIT

    CLICK_SUBMIT --> VERIFY_CONFIRM{"Confirmation Signature Found?"}
    VERIFY_CONFIRM -->|Yes: 'Thank you for applying'| SET_CONFIRMED["Status: CONFIRMED<br>Record Ref Number & Final Screenshot"]
    VERIFY_CONFIRM -->|No: Uncertain / Custom Redirect| SET_VERIFY["Status: VERIFICATION_REQUIRED<br>Record Screenshot for Manual Audit"]
```

---

## 6. Database Entity-Relationship Model

```mermaid
erDiagram
    UserProfile ||--o{ ResumeDocument : "uploads"
    UserProfile ||--o{ Application : "submits"
    UserProfile ||--o{ JobMatch : "evaluates"
    UserProfile ||--o{ ApplicationDraft : "generates"
    UserProfile ||--o{ ProfileSnapshot : "snapshots"

    JobListing ||--o{ JobMatch : "matches"
    JobListing ||--o{ Application : "targets"
    JobListing ||--o{ ApplicationDraft : "drafts"

    UserProfile {
        int id PK
        string full_name
        string email
        string phone
        string location
        string headline
        text summary
        text skills "JSON / CSV"
        text target_roles "JSON"
        float experience_years
        text educations "JSON"
        text experiences "JSON"
        datetime created_at
        datetime updated_at
    }

    ProfileSnapshot {
        int id PK
        int user_id FK
        string action_type
        text snapshot_data "Serialized Profile"
        datetime created_at
    }

    JobListing {
        int id PK
        string source
        string external_id
        string title
        string company
        string location
        text description
        text requirements "JSON"
        string application_url
        string fingerprint "Unique SHA256"
        string status
        datetime posted_date
        datetime created_at
    }

    JobMatch {
        int id PK
        int job_id FK
        int user_id FK
        float overall_score
        float skills_score
        float experience_score
        float education_score
        string status
        text rationale
        text missing_criteria
        text positive_matches
        string match_fingerprint "Cache Hash"
        boolean is_fallback
        text low_information_warning
        datetime evaluated_at
    }

    Application {
        int id PK
        int job_id FK
        int user_id FK
        int resume_id FK
        int draft_id FK
        string status
        boolean requires_approval
        boolean is_user_approved
        string confirmation_reference
        string last_step
        text error_message
        datetime approved_at
        datetime submitted_at
        datetime created_at
    }

    ResumeDocument {
        int id PK
        int user_id FK
        string filename
        string file_path
        string file_type
        text extracted_text
        boolean is_primary
        datetime created_at
    }
```

---

## 7. Security, Secrets & Compliance Architecture

1. **Zero Secret Leakage**:
   - Secrets are loaded via `pydantic-settings` anchored to the absolute project root `.env`.
   - Logging redaction filter (`SecretRedactingFilter`) intercepts all log records, masking strings matching `gsk_`, bearer tokens, email passwords, and database credentials with `***REDACTED***`.
   - Health and config endpoints (`/api/v1/config`, `/api/v1/health/ai`) never output raw keys; only non-reversible 8-character fingerprints (`sha256[:8]`) and presence flags are reported.
2. **SSRF (Server-Side Request Forgery) Prevention**:
   - `validate_external_url` enforces RFC 3986 compliance, permits only `http` and `https` schemes, and blocks private/local IP ranges (127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, loopback).
3. **Path Traversal Shield**:
   - Resume uploads and generated documents are strictly validated using `validate_file_path` against dedicated storage directories. Filenames are stripped of path delimiters (`../`, `..\`) via `sanitize_filename`.
4. **Platform Compliance Boundaries**:
   - Platforms prohibiting direct automated scraping (LinkedIn, Internshala, Glassdoor) are classified as **User-Assisted**. Automated web scraping is not performed against them; instead, users supply listing URLs, and client-permitted JSON-LD metadata extraction is performed.
