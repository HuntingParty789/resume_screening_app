import re
import pandas as pd
import streamlit as st
import requests
import PyPDF2
import docx2txt
import tempfile
import os

# Groq setup
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

def call_llm(prompt):
    if not GROQ_API_KEY:
        st.error("Groq API key missing. Set GROQ_API_KEY!")
        return ""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.1
    }
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=60)
        if not response.ok:
            st.error(f"Groq API error {response.status_code}: {response.text}")
            return ""
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"LLM call failed: {str(e)}")
        return ""

def score_to_confidence(score):
    if score >= 85:
        return "🟢 High", "success"
    elif score >= 70:
        return "🟡 Medium", "warning"
    else:
        return "🔴 Low", "error"

def build_candidate_prompt(jd, resume_text):
    return f"""You are an expert HR AI assistant specializing in candidate evaluation.
JOB DESCRIPTION:
{jd}
CANDIDATE RESUME:
{resume_text}
TASK: Provide a comprehensive assessment using this exact format:
score: [0-100]
Strengths: [2-3 key strengths]
Weaknesses: [1-2 areas for improvement]
Recommendation: [One clear sentence: Should we hire/interview/pass and why?]
"""

def parse_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(file_bytes)
        text = " ".join([page.extract_text() or "" for page in reader.pages])
        return text.strip() if text.strip() else "Could not extract text from PDF."
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"

def parse_docx(file_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes.read())
            tmp.flush()
            text = docx2txt.process(tmp.name)
            os.unlink(tmp.name)
        return text.strip() if text.strip() else "Could not extract text from DOCX."
    except Exception as e:
        return f"Error parsing DOCX: {str(e)}"

def parse_resume(filename, fileobj):
    fileobj.seek(0)
    if filename.lower().endswith(".pdf"):
        return parse_pdf(fileobj)
    elif filename.lower().endswith(".docx"):
        return parse_docx(fileobj)
    else:
        return "❌ Unsupported file type. Please upload PDF or DOCX files."

st.set_page_config(page_title="AI Resume Screening Tool", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.main-header { text-align: center; margin: 0 0 2em 0; }
.candidate-card {
    background: #fff;
    color: #222 !important;
    padding: 2rem;
    border-radius: 15px;
    border-left: 8px solid #667eea;
    margin: 1.5rem 0;
    font-size: 1.1em;
    box-shadow: 0 2px 16px rgba(70,78,105,.05);
}
.candidate-card strong { color: #222; }
.stTextInput label, .stTextArea label { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🎯 AI-Powered Resume Screening Tool</h1>
    <p>Upload PDF/DOCX resumes. Get best-match recommendations with confidence levels.<br>
    Type ANY follow-up Q in the chat box and get instant answers. Box always resets after each question.</p>
</div>
""", unsafe_allow_html=True)

if "df" not in st.session_state:
    st.session_state["df"] = pd.DataFrame()
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []
if "last_asked" not in st.session_state:
    st.session_state.last_asked = ""
if "last_q_prompt" not in st.session_state:
    st.session_state.last_q_prompt = ""

job_desc = st.text_area("📋 Job Description", height=150, placeholder="Paste the job description here...")
uploaded_files = st.file_uploader("📎 Upload Candidate Resumes (.pdf / .docx)", type=["pdf", "docx"], accept_multiple_files=True)
results = []

if st.button("🚀 Analyze Resumes", disabled=not (uploaded_files and job_desc.strip())):
    for file in uploaded_files:
        text = parse_resume(file.name, file)
        prompt = build_candidate_prompt(job_desc, text)
        llm_result = call_llm(prompt)
        score_match = re.search(r"score\s*[:=\-]*\s*(\d+)", llm_result or "", re.I)
        score = int(score_match.group(1)) if score_match else 0
        confidence, badge_type = score_to_confidence(score)
        strengths = weaknesses = recommendation = ""
        try:
            strengths = re.search(r"Strengths:\s*(.*?)(?=Weaknesses:|Recommendation:|$)", llm_result, re.S).group(1).strip()
            weaknesses = re.search(r"Weaknesses:\s*(.*?)(?=Recommendation:|$)", llm_result, re.S).group(1).strip()
            recommendation = re.search(r"Recommendation:\s*(.*?)(?=\n\n|$)", llm_result, re.S).group(1).strip()
        except Exception:
            pass
        results.append({
            "Filename": file.name,
            "Confidence": confidence,
            "Score": score,
            "Strengths": strengths,
            "Weaknesses": weaknesses,
            "Recommendation": recommendation,
            "Raw": llm_result
        })

    df = pd.DataFrame(results)
    st.session_state["df"] = df
    st.session_state.qa_history = []
    st.session_state.last_asked = ""
    st.session_state.last_q_prompt = ""
    if df.empty or df.Score.max() == 0:
        st.error("No valid resume analysis was generated. Check your resumes and connection/API key.")
    else:
        best_index = df['Score'].astype(int).idxmax()
        best_row = df.iloc[best_index]
        st.markdown("## 🏆 Top Candidate Recommendation")
        st.markdown(f"""
            <div class="candidate-card">
            <h3>📄 {best_row['Filename']}</h3>
            <p><strong>Confidence Level:</strong> {best_row['Confidence']}</p>
            <p><strong>💪 Strengths:</strong><br>{best_row['Strengths']}</p>
            <p><strong>⚠️ Weaknesses:</strong><br>{best_row['Weaknesses']}</p>
            <p><strong>🎯 Recommendation:</strong><br>{best_row['Recommendation']}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("## 📊 All Candidates")
        st.dataframe(df[['Filename', 'Confidence', 'Strengths', 'Weaknesses', 'Recommendation']], width="stretch")

st.markdown("## 🤔 HR Follow-up Q&A (Automatic Chat Mode)")
df = st.session_state["df"]

if st.session_state.qa_history:
    st.markdown("### 💬 Your Q&A History")
    for i, (q, a) in enumerate(st.session_state.qa_history):
        st.markdown(f"**Q{i+1}:** {q}")
        st.markdown(f"> **A{i+1}:** {a}")

# Input box always available; answers immediately and auto-clears
question = st.text_input("Type your HR question and press Enter...", value="", key="auto_chat", autocomplete="off")
MAX_LEN = 700

if (
    question.strip()
    and question != st.session_state.last_asked
    and not df.empty
):
    analyses_context = "\n\n".join(
        f"Candidate {row['Filename']} analysis:\n{str(row['Raw'])[:MAX_LEN]}"
        for _, row in df.iterrows()
    )
    q_prompt = (
        "The informations are given below....\n\n"
        f"{analyses_context}\n\n"
        f"---\n\nQuestion: {question}\nHR Assistant's answer:"
    )
    reply = call_llm(q_prompt)
    st.session_state.qa_history.append((question, reply if reply and reply.strip() else "**No answer returned or error.**"))
    st.session_state.last_asked = question
    st.session_state.last_q_prompt = q_prompt
    st.experimental_rerun()

elif question and df.empty:
    st.warning("No candidate analyses found. Please run 'Analyze Resumes' first.")

if st.session_state.qa_history and st.session_state.last_q_prompt:
    with st.expander("Show Last LLM Prompt and Analysis Context (debug only)"):
        st.code(st.session_state.last_q_prompt, language="markdown")

st.markdown("---")
if not st.session_state["df"].empty:
    csv = st.session_state["df"].drop(columns=["Raw"]).to_csv(index=False)
    st.download_button("📥 Download Results (CSV)", csv, file_name="candidate_recommendations.csv")

st.caption("LLM-powered screening. For real-world hiring, always review results with a human expert.")
