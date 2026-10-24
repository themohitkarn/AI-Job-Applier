"""Configurable prompt templates for AI application content generation."""

COVER_LETTER_SYSTEM_PROMPT = """You are an elite executive career strategist and professional copywriter.
CRITICAL INTEGRITY RULES:
1. Use ONLY the verified candidate background, skills, experiences, and education provided.
2. NEVER invent, hallucinate, or exaggerate qualifications, past employers, degrees, metrics, or achievements.
3. If the candidate lacks a specific skill requested by the job description, do NOT claim they possess it. Instead, focus positively on their real verified strengths.
4. Maintain a professional, confident, tailored, and concise tone.
"""

COVER_LETTER_USER_TEMPLATE = """
Target Job Information:
- Role Title: {job_title}
- Company: {company_name}
- Location: {job_location}
- Description & Requirements:
{job_description}

Candidate Profile (Verified):
- Name: {candidate_name}
- Email: {candidate_email}
- Phone: {candidate_phone}
- Experience Level: {experience_years} years
- Verified Skills: {candidate_skills}
- Work Experience: {candidate_experience}
- Education: {candidate_education}

Additional Candidate Instructions:
{custom_instructions}

Please write an impactful, tailored cover letter.
Return your response strictly in the following format:
Subject: [Application Subject Line]

[Body of Cover Letter]
"""

COLD_EMAIL_USER_TEMPLATE = """
Target Job Information:
- Role Title: {job_title}
- Company: {company_name}
- Hiring Context: {job_description}

Candidate Profile (Verified):
- Name: {candidate_name}
- Verified Skills: {candidate_skills}
- Key Experience: {candidate_experience}

Additional Instructions:
{custom_instructions}

Write a crisp, high-conversion cold outreach email (under 150 words) to the hiring manager or recruiter.
Return your response strictly in this format:
Subject: [Catchy, Professional Subject Line]

[Body of Email]
"""
