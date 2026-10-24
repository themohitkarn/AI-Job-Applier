"""AI Job Assistant & Outreach Streamlit Tool.

Preserved legacy outreach tool upgraded to utilize modular settings and configuration.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
from groq import Groq

# Load modular application settings
try:
    from app.core.config import get_settings
    settings = get_settings()
    DEFAULT_GROQ_KEY = settings.groq_api_key or ""
    DEFAULT_GROQ_MODEL = settings.groq_model
    DEFAULT_EMAIL = settings.sender_email or ""
    DEFAULT_PASSWORD = settings.sender_password or ""
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    DEFAULT_GROQ_KEY = os.getenv("GROQ_API_KEY", "")
    DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    DEFAULT_EMAIL = os.getenv("SENDER_EMAIL", "")
    DEFAULT_PASSWORD = os.getenv("SENDER_PASSWORD", "")

# Page Config
st.set_page_config(page_title="AI Job Assistant & Outreach", page_icon="🚀", layout="wide")

st.title("🚀 AI-Powered Job Referral & Application Dashboard")
st.write("Roz-roz ke cold emails ka stress khatam! Bol kar ya type karke apna mail generate karo.")

# Sidebar for Configuration (.env loaded)
st.sidebar.header("⚙️ Configuration (.env loaded)")
groq_api_key = st.sidebar.text_input("Groq API Key", value=DEFAULT_GROQ_KEY, type="password")
groq_model = st.sidebar.text_input("Groq Model", value=DEFAULT_GROQ_MODEL)

st.sidebar.markdown("---")
st.sidebar.header("📧 Sender Email Settings")
sender_email = st.sidebar.text_input("Your Email (Gmail)", value=DEFAULT_EMAIL)
sender_password = st.sidebar.text_input("Gmail App Password", value=DEFAULT_PASSWORD, type="password")

# Automation Control Toggle
st.sidebar.markdown("---")
st.sidebar.header("🎛️ Controls")
auto_send_toggle = st.sidebar.toggle("⚡ Enable Direct Auto-Send", value=False, help="Agar ON karoge, toh generate hote hi mail seedha HR ko chala jayega.")

# Main Form Layout
col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input("🏢 Company Name", placeholder="e.g., Google, Microsoft, Startup")
    hr_email = st.text_input("📧 HR / Recruiter Email", placeholder="hr@company.com")

with col2:
    role_category = st.selectbox(
        "🎯 Target Role / Internship",
        [
            "AI/ML Engineer", 
            "Software Developer (SDE)", 
            "Full Stack Developer", 
            "Backend Developer", 
            "Frontend Developer", 
            "Web Developer (React/Next.js)", 
            "React Native Mobile App Developer", 
            "Data Scientist / Data Analyst", 
            "DevOps Engineer", 
            "Software Testing & QA Engineer",
            "Python Developer",
            "General IT / Software Intern"
        ]
    )
    
    job_description = st.text_area("📋 Paste Job Description (Optional)", placeholder="Paste JD here to customize the email...")

st.markdown("---")
st.subheader("🎙️ Voice Typing & Custom Instructions for AI")
st.write("Click 'Start Voice Typing', boliye, aur turant mic band hokar text box mein aa jayega:")

# Optimized Speech-to-Text with instant auto-stop after speech finishes
speech_box_html = """
<div style="background-color: #1e1e1e; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
    <button onclick="startQuickSpeech()" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px;">
        🔴 Start Voice Typing (Fast Auto-Stop)
    </button>
    <span id="mic-status" style="margin-left: 12px; color: #a3a3a3; font-size: 13px; font-family: sans-serif;">Ready...</span>
</div>

<script>
function startQuickSpeech() {
    const status = document.getElementById('mic-status');
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        status.innerText = "Speech recognition not supported in this browser. Use Chrome/Edge.";
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = 'en-IN'; 
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    // Quick stop optimization
    recognition.onaudiostart = function() {
        status.innerText = "🎙️ Listening... Speak now!";
    };
    
    recognition.onspeechend = function() {
        status.innerText = "⚡ Speech ended, closing mic...";
        recognition.stop();
    };
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        status.innerText = "✅ Captured: " + transcript;
        
        // Find Streamlit text area and inject text
        const textareas = window.parent.document.querySelectorAll('textarea');
        for (let i = 0; i < textareas.length; i++) {
            if (textareas[i].placeholder && textareas[i].placeholder.includes("Jaise:")) {
                textareas[i].value += (textareas[i].value ? " " : "") + transcript;
                textareas[i].dispatchEvent(new Event('input', { bubbles: true }));
                break;
            }
        }
    };
    
    recognition.onerror = function(event) {
        status.innerText = "❌ Error: " + event.error;
    };
    
    recognition.onend = function() {
        if (!status.innerText.includes("Captured") && !status.innerText.includes("Error")) {
            status.innerText = "⏹️ Mic closed.";
        }
    };
    
    recognition.start();
}
</script>
"""

import streamlit.components.v1 as components
components.html(speech_box_html, height=75)

# Visible Text Box
custom_notes = st.text_area(
    "Candidate Instructions Box (Visible Text)", 
    placeholder="Jaise: 'Mujhe Python aur React Native ka experience mention karna hai'...",
    key="instruction_box"
)

# Resume Upload
uploaded_resume = st.file_uploader("📄 Upload Your Resume (PDF/Text)", type=["pdf", "txt"])

# Single Action Button
if st.button("✨ Generate & Process Email", type="primary"):
    if not groq_api_key:
        st.error("Groq API Key missing hai! .env file ya sidebar check karo.")
    elif not company_name or not hr_email:
        st.error("Company Name aur HR Email daalna zaroori hai!")
    else:
        with st.spinner("AI is crafting your hyper-personalized professional email..."):
            try:
                # Initialize Groq Client
                client = Groq(api_key=groq_api_key)
                
                prompt = f"""
                You are an expert career coach and professional copywriter. Write a hyper-personalized, crisp, and impactful cold email for a job/internship application.
                
                Target Company: {company_name}
                Target Role/Internship: {role_category}
                Job Description Details: {job_description if job_description else 'Standard industry requirements for this role.'}
                Additional Instructions: {custom_notes if custom_notes else 'None'}
                
                The candidate has strong skills in Python, Machine Learning, Agentic GenAI, full-stack, and mobile app development.
                Keep it professional, confident, not too long. IMPORTANT: Return the output strictly in this format:
                Subject: [Write a catchy subject line here]
                [Email Body Here]
                """
                
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=groq_model,
                )
                
                email_raw = chat_completion.choices[0].message.content
                
                # Separate Subject and Body
                if "Subject:" in email_raw:
                    parts = email_raw.split("\n", 1)
                    subject_line = parts[0].replace("Subject:", "").strip()
                    email_body = parts[1].strip() if len(parts) > 1 else email_raw
                else:
                    subject_line = f"Application for {role_category} position at {company_name}"
                    email_body = email_raw

                st.success("✅ Email Generated Successfully!")
                st.subheader("Generated Email Preview:")
                st.code(email_raw, language="markdown")
                
                # Check if Auto-Send Toggle is ON
                if auto_send_toggle:
                    if not sender_email or not sender_password:
                        st.error("Auto-send on hai, lekin Sender Email ya App Password missing hai .env mein!")
                    else:
                        with st.spinner("Auto-sending email via SMTP..."):
                            msg = MIMEMultipart()
                            msg['From'] = sender_email
                            msg['To'] = hr_email
                            msg['Subject'] = subject_line
                            msg.attach(MIMEText(email_body, 'plain'))
                            
                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(sender_email, sender_password)
                            server.sendmail(sender_email, hr_email, msg.as_string())
                            server.quit()
                            
                            st.success(f"🎉 Email automatically sent to {hr_email}!")
                else:
                    st.info("ℹ️ Auto-Send OFF hai. Aapne email preview dekh liya hai, ise copy karke bhej sakte hain.")

            except Exception as e:
                st.error(f"Kuch error aa gaya: {e}")
