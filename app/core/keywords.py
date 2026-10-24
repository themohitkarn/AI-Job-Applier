"""Taxonomy, keyword groups, synonyms, fresher patterns, and work mode detection.

Centralizes all configurable job search keywords, technical skill synonyms,
fresher/internship indicators, and work mode classifications.
"""
from typing import Dict, List, Optional, Set, Tuple
import json
import re


# Five core skill & job title categories requested by user
DEFAULT_KEYWORD_GROUPS: Dict[str, List[str]] = {
    "ai_ml": [
        "AI Engineer",
        "AI Developer",
        "Machine Learning Engineer",
        "ML Intern",
        "Generative AI",
        "GenAI Developer",
        "LLM Application Developer",
        "Agentic AI",
        "AI Agent Developer",
        "Multi-Agent Systems",
        "NLP Engineer",
        "Deep Learning Engineer",
        "RAG Developer",
        "Retrieval-Augmented Generation",
        "Prompt Engineering",
        "AI Automation",
        "AI Research Intern",
    ],
    "python_backend": [
        "Python Developer",
        "Junior Python Developer",
        "Backend Developer",
        "FastAPI Developer",
        "API Developer",
        "Software Developer",
        "Automation Developer",
    ],
    "web_fullstack": [
        "Web Developer",
        "Full-Stack Developer",
        "PHP Developer",
        "Laravel Developer",
        "Node.js Developer",
        "JavaScript Developer",
        "HTML",
        "CSS",
        "Bootstrap",
        "Tailwind CSS",
        "Frontend Developer",
        "Backend Web Developer",
    ],
    "software_engineering": [
        "Software Engineer",
        "Software Development Engineer",
        "SDE",
        "SDE Intern",
        "Graduate Software Engineer",
        "Junior Software Engineer",
        "Software Trainee",
        "Graduate Engineer Trainee",
        "Technical Intern",
    ],
    "database_data": [
        "SQL Developer",
        "MySQL Developer",
        "SQLite",
        "DBMS",
        "Database Developer",
        "Junior Data Analyst",
        "Python Data Intern",
        "Data Engineering Intern",
        "Database Intern",
    ],
}


# Technical synonyms and transferable skills mapping
# Maps skill -> related/transferable technical skills, variations, and frameworks
TECHNICAL_SYNONYMS: Dict[str, List[str]] = {
    "fastapi": ["python", "api", "backend", "rest api", "web api", "asgi", "pydantic", "microservices"],
    "flask": ["python", "api", "backend", "web development", "rest api"],
    "django": ["python", "backend", "web development", "orm", "full-stack"],
    "python": ["backend", "scripting", "programming", "python3", "data analysis", "automation"],
    "sql": ["mysql", "sqlite", "postgresql", "postgres", "dbms", "database", "rdbms", "relational database", "queries", "sql developer"],
    "mysql": ["sql", "database", "dbms", "relational database", "rdbms", "backend"],
    "sqlite": ["sql", "database", "dbms", "relational database", "embedded database"],
    "postgresql": ["sql", "database", "dbms", "postgres", "relational database", "rdbms"],
    "dbms": ["sql", "database", "mysql", "sqlite", "postgresql", "data store"],
    "database": ["sql", "dbms", "mysql", "sqlite", "relational database", "data modeling"],
    "genai": ["generative ai", "ai", "llm", "large language models", "prompt engineering", "rag", "langchain", "llamaindex", "artificial intelligence"],
    "generative ai": ["genai", "ai", "llm", "large language models", "prompt engineering", "rag", "langchain", "llamaindex"],
    "llm": ["large language models", "genai", "generative ai", "ai", "prompt engineering", "rag", "transformers", "foundation models"],
    "rag": ["retrieval-augmented generation", "retrieval augmented generation", "llm", "genai", "ai", "vector database", "embeddings", "vector search"],
    "agentic ai": ["ai agent", "ai agents", "multi-agent", "multi-agent systems", "agentic", "ai", "autonomous agents", "langgraph", "crewai", "autogen"],
    "machine learning": ["ml", "ai", "artificial intelligence", "scikit-learn", "data science", "predictive modeling"],
    "ml": ["machine learning", "ai", "data science", "artificial intelligence"],
    "nlp": ["natural language processing", "text processing", "ai", "ml", "spacy", "nltk", "huggingface", "llm"],
    "deep learning": ["neural networks", "ai", "ml", "pytorch", "tensorflow", "keras"],
    "html": ["html5", "frontend", "web", "web development", "markup", "web developer"],
    "css": ["css3", "tailwind", "tailwind css", "bootstrap", "frontend", "web", "styling", "responsive design"],
    "tailwind": ["tailwind css", "css", "frontend", "styling"],
    "tailwind css": ["tailwind", "css", "frontend", "styling"],
    "bootstrap": ["css", "frontend", "responsive design", "ui framework"],
    "javascript": ["js", "frontend", "web development", "es6", "node.js", "nodejs", "typescript"],
    "node.js": ["nodejs", "node", "javascript", "backend", "express"],
    "php": ["backend", "web development", "laravel", "lamp", "full-stack"],
    "laravel": ["php", "backend", "web development", "mvc", "full-stack"],
    "sde": ["software engineer", "software development engineer", "software developer", "developer", "programmer"],
    "software engineer": ["software development engineer", "software developer", "developer", "sde", "programmer", "software engineering"],
    "software developer": ["software engineer", "developer", "programmer", "sde", "software development"],
    "prompt engineering": ["llm", "genai", "generative ai", "ai prompt", "few-shot", "ai developer"],
    "automation": ["scripting", "playwright", "selenium", "browser automation", "python automation", "testing"],
    "data analyst": ["sql", "python", "data analysis", "pandas", "visualization", "bi", "reporting"],
}


# Fresher, Entry-Level, Intern, and Trainee indicators
FRESHER_INDICATORS: List[str] = [
    "fresher",
    "freshers",
    "intern",
    "interns",
    "internship",
    "internships",
    "trainee",
    "trainees",
    "graduate",
    "graduates",
    "campus",
    "entry level",
    "entry-level",
    "junior",
    "jr",
    "jr.",
    "apprentice",
    "apprenticeship",
    "0-1 year",
    "0-2 years",
    "0 to 1 year",
    "0 to 2 years",
    "0+ year",
    "0+ years",
    "zero experience",
    "no experience required",
    "no experience needed",
    "no prior experience",
    "new grad",
    "new graduate",
    "fresh graduate",
    "recent graduate",
    "recent graduates",
    "entry level engineer",
    "associate engineer",
    "trainee engineer",
    "graduate engineer trainee",
    "get",
    "sde intern",
    "technical intern",
    "ml intern",
    "python data intern",
]


# Regex patterns for mandatory vs preferred qualification separation
MANDATORY_PATTERNS = [
    re.compile(r"\b(must have|required|requirements|mandatory|essential|minimum qualifications?|you must|needed|prerequisites?)\b", re.IGNORECASE),
    re.compile(r"\b(strictly required|core requirements?|qualification:)\b", re.IGNORECASE),
]

PREFERRED_PATTERNS = [
    re.compile(r"\b(preferred|nice to have|plus|bonus|good to have|advantageous|desired|optional|not required|an asset|beneficial|ideal)\b", re.IGNORECASE),
    re.compile(r"\b(preferred qualifications?|bonus points? for|what would make you stand out|helpful to have)\b", re.IGNORECASE),
]

# Work mode classification patterns
WORK_MODE_PATTERNS = {
    "remote": re.compile(r"\b(remote|work from home|wfh|telecommute|anywhere|distributed|virtual|remote-friendly|worldwide)\b", re.IGNORECASE),
    "hybrid": re.compile(r"\b(hybrid|flexible remote|partially remote|split week|hybrid-remote|days remote)\b", re.IGNORECASE),
    "on-site": re.compile(r"\b(on-site|onsite|in-office|in person|office-based|on site|in-person)\b", re.IGNORECASE),
}


def detect_work_modes(location: Optional[str] = None, text: Optional[str] = None) -> List[str]:
    """Classify listing work modes (remote, hybrid, on-site) based on location and text."""
    combined = f"{location or ''} {text or ''}".lower()
    modes: Set[str] = set()

    if WORK_MODE_PATTERNS["remote"].search(combined):
        modes.add("remote")

    if WORK_MODE_PATTERNS["hybrid"].search(combined):
        modes.add("hybrid")

    if WORK_MODE_PATTERNS["on-site"].search(combined):
        modes.add("on-site")

    # If location is a specific physical city/country without explicit remote/hybrid tag, treat as on-site
    loc_clean = (location or "").strip().lower()
    if loc_clean and loc_clean not in ("remote", "anywhere", "worldwide", "distributed", "virtual"):
        if not modes:
            modes.add("on-site")

    # If completely unspecified, default to remote/worldwide friendly
    if not modes:
        modes.add("remote")

    return sorted(list(modes))


def detect_fresher_friendly(
    title: str,
    description: str,
    requirements: Optional[List[str]] = None,
    experience_level: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Determine whether a vacancy welcomes freshers, interns, graduates, or candidates with 0-1 yr exp."""
    reasons: List[str] = []
    combined_text = f"{title} {description} {' '.join(requirements or [])}".lower()
    title_lower = title.lower()

    # 1. Title contains direct fresher/intern/trainee/graduate indicators
    for ind in FRESHER_INDICATORS:
        pattern = r"\b" + re.escape(ind) + r"\b"
        if re.search(pattern, title_lower):
            reasons.append(f"Job title explicitly matches entry-level indicator '{ind}'")
            return True, reasons

    # 2. Experience level metadata tag
    if experience_level:
        exp_lvl_clean = experience_level.strip().lower()
        if any(term in exp_lvl_clean for term in ["entry", "intern", "trainee", "junior", "graduate"]):
            reasons.append(f"Posting metadata indicates '{experience_level}' experience level")
            return True, reasons

    # 3. Check for 0 experience / new grad phrases in description
    zero_exp_patterns = [
        r"\b(0\s*-\s*[12]\s*years?(?:\s+of)?\s+experience)\b",
        r"\b(0\s*\+\s*years?(?:\s+of)?\s+experience)\b",
        r"\b(no\s+experience\s+(?:required|needed))\b",
        r"\b(fresh\s+graduates?|recent\s+graduates?|new\s+grads?)\b",
        r"\b(campus\s+recruitment|campus\s+hiring|freshers?\s+welcome)\b",
        r"\b(internship|trainee\s+program|entry\s+level)\b",
    ]
    for pat in zero_exp_patterns:
        m = re.search(pat, combined_text, re.IGNORECASE)
        if m:
            reasons.append(f"Description accepts early-career / entry-level candidates: '{m.group(0)}'")
            return True, reasons

    # 4. Check if maximum required experience extracted is <= 1 or 2 years without "senior"/"lead" in title
    if not any(senior_term in title_lower for senior_term in ["senior", "sr", "sr.", "lead", "principal", "staff", "director", "head", "manager"]):
        exp_match = re.search(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", combined_text)
        if exp_match:
            years = int(exp_match.group(1))
            if years <= 1:
                reasons.append(f"Experience requirement is accessible for freshers ({years} yr requested)")
                return True, reasons

    return False, reasons


def split_mandatory_vs_preferred(
    description: str,
    requirements: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Partition text bullets and sentences into mandatory vs preferred requirements."""
    mandatory: List[str] = []
    preferred: List[str] = []

    # Process explicit requirement list first
    for req in requirements or []:
        is_pref = any(p.search(req) for p in PREFERRED_PATTERNS)
        if is_pref:
            preferred.append(req.strip())
        else:
            mandatory.append(req.strip())

    # Process sentences / lines from description
    lines = [line.strip("- *• \t") for line in description.splitlines() if line.strip()]
    for line in lines:
        if len(line) < 10 or len(line) > 200:
            continue
        # Skip section header lines (e.g. "Requirements:", "Preferred Qualifications:")
        if re.match(r"^(requirements|preferred qualifications|qualifications|responsibilities|what we offer|about the role|nice to have)[:\s]*$", line, re.IGNORECASE):
            continue
        is_pref = any(p.search(line) for p in PREFERRED_PATTERNS)
        is_mand = any(m.search(line) for m in MANDATORY_PATTERNS)
        if is_pref and line not in preferred:
            preferred.append(line)
        elif is_mand and line not in mandatory:
            mandatory.append(line)

    return mandatory, preferred


def match_skills_with_synonyms(
    candidate_skills: List[str],
    job_text: str,
    job_requirements: Optional[List[str]] = None,
) -> Dict[str, any]:
    """Inspect full job text and match candidate skills with synonym & transferable technology expansion."""
    job_text_lower = job_text.lower()
    direct_matches: List[str] = []
    synonym_matches: Dict[str, str] = {}
    matched_job_terms: Set[str] = set()

    normalized_candidate_skills = {s.strip(): s.strip().lower() for s in candidate_skills}

    for original_skill, skill_lower in normalized_candidate_skills.items():
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, job_text_lower):
            direct_matches.append(original_skill)
            matched_job_terms.add(skill_lower)
            continue

        # Look up synonyms for this skill
        synonyms = TECHNICAL_SYNONYMS.get(skill_lower, [])
        for syn in synonyms:
            syn_pattern = r"\b" + re.escape(syn) + r"\b"
            if re.search(syn_pattern, job_text_lower):
                synonym_matches[original_skill] = f"Matches '{syn}' in job listing (Transferable synergy)"
                matched_job_terms.add(syn)
                break

    # Also check if job requirements mention skills that map back to candidate skills
    for req in job_requirements or []:
        req_lower = req.lower()
        for original_skill, skill_lower in normalized_candidate_skills.items():
            if original_skill in direct_matches or original_skill in synonym_matches:
                continue
            # Check if requirement matches skill or its synonyms
            if skill_lower in req_lower:
                direct_matches.append(original_skill)
                matched_job_terms.add(skill_lower)
                break
            synonyms = TECHNICAL_SYNONYMS.get(skill_lower, [])
            if any(syn in req_lower for syn in synonyms):
                matched_syn = next(syn for syn in synonyms if syn in req_lower)
                synonym_matches[original_skill] = f"Maps to required '{matched_syn}' (Transferable skill)"
                matched_job_terms.add(matched_syn)
                break

    return {
        "direct_matches": direct_matches,
        "synonym_matches": synonym_matches,
        "matched_job_terms": list(matched_job_terms),
        "total_matched_skills_count": len(direct_matches) + len(synonym_matches),
    }


def discover_title_variations(job_title: str, existing_keywords: Optional[List[str]] = None) -> List[str]:
    """Extract new potential job-title variations from an actual job title."""
    clean_title = re.sub(r"[\(\[\{].*?[\)\]\}]", "", job_title).strip()
    variations: List[str] = []
    existing_lower = {k.lower() for k in (existing_keywords or [])}

    # Split common composite titles (e.g. "Python Developer / Data Engineer" or "SDE - Backend")
    parts = re.split(r"[/|•\-\–\—]", clean_title)
    for part in parts:
        cleaned = part.strip()
        if len(cleaned) >= 4 and cleaned.lower() not in existing_lower:
            variations.append(cleaned)

    return variations
