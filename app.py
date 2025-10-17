import re
import pandas as pd
import streamlit as st
import requests
import PyPDF2
import docx2txt
import tempfile

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else None
GROQ_MODEL = "llama-3.1-8b-instant"

def call_llm(prompt):
    if not GROQ_API_KEY:
        st.error("Groq API key missing. Set GROQ_API_KEY in .env/secrets!")
        return ""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.0
    }
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        if not response.ok:
            st.error(f"Groq API error {response.status_code}: {response.text}")
            return ""
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"LLM call failed: {e}")
        return ""

def score_to_confidence(score):
    if score >= 80:
        return "High"
    elif score >= 60:
        return "Medium"
    else:
        return "Low"

def build_candidate_prompt(jd, resume_text):
    return (
        f"You are an expert HR AI assistant.\n"
        f"Job Description:\n{jd}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        f"Assess: "
        f"1) Candidate fit score for this JD (label as 'score:' 0-100, higher=better), "
        f"2) Strengths (label 'Strengths:'), "
        f"3) Weaknesses (label 'Weaknesses:'), "
        f"4) Clear, short hiring recommendation (label 'Recommendation:').\n"
        f"Output in this format: score: xx Strengths: ... Weaknesses: ... Recommendation: ..."
        f"Do not randomly change your score for the same input."
    )

def parse_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(file_bytes)
        text = " ".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        return f"ERROR parsing PDF: {e}"

def parse_docx(file_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes.read())
            tmp.flush()
            text = docx2txt.process(tmp.name)
        return text.strip()
    except Exception as e:
        return f"ERROR parsing DOCX: {e}"

def parse_resume(filename, fileobj):
    if filename.lower().endswith(".pdf"):
        return parse_pdf(fileobj)
    elif filename.lower().endswith(".docx"):
        return parse_docx(fileobj)
    else:
        return "Unsupported file type"

st.title("Best-fit Candidate Confidence Recommendations (With Upload)")

job_desc = st.text_area("Paste your job description", height=140)
uploaded_files = st.file_uploader(
    "Upload one or more resumes (.pdf, .docx)", type=["pdf", "docx"], accept_multiple_files=True
)

if st.button("Analyze Uploaded Resumes") and uploaded_files and job_desc.strip():
    results = []
    for file in uploaded_files:
        file.seek(0)
        text = parse_resume(file.name, file)
        prompt = build_candidate_prompt(job_desc, text)
        llm_result = call_llm(prompt)
        score_match = re.search(r"score\s*[:=\-]*\s*(\d+)", llm_result or "", re.I)
        score = int(score_match.group(1)) if score_match else 0
        confidence = score_to_confidence(score)
        strengths, weaknesses, recommendation = "", "", ""
        try:
            strengths = re.search(r"Strengths:\s*(.*?)(Weaknesses:|Recommendation:|$)", llm_result, re.S).group(1).strip()
            weaknesses = re.search(r"Weaknesses:\s*(.*?)(Recommendation:|$)", llm_result, re.S).group(1).strip()
            recommendation = re.search(r"Recommendation:\s*(.*)", llm_result, re.S).group(1).strip()
        except Exception:
            pass
        results.append({
            "Filename": file.name,
            "Confidence": confidence,
            "Strengths": strengths,
            "Weaknesses": weaknesses,
            "Recommendation": recommendation
        })
    df = pd.DataFrame(results)
    df['Confidence_sort'] = df['Confidence'].map({'High': 2, 'Medium': 1, 'Low': 0})
    top_df = df.sort_values("Confidence_sort", ascending=False).head(1)
    st.header("Most Suitable Candidate Recommendation")
    for _, row in top_df.iterrows():
        st.subheader(row['Filename'])
        st.markdown(f"**Confidence Level:** {row['Confidence']}")
        st.markdown(f"**Strengths:** {row['Strengths']}")
        st.markdown(f"**Weaknesses:** {row['Weaknesses']}")
        st.markdown(f"**Recommendation:** {row['Recommendation']}")
    st.header("All Candidates, Ranked by Confidence")
    st.dataframe(df.drop(columns=["Confidence_sort"]), use_container_width=True)
    csv = df.drop(columns=["Confidence_sort"]).to_csv(index=False)
    st.download_button("Download Results (CSV)", csv, file_name="candidate_recommendations.csv")

else:
    st.info("Paste a job description, upload resumes, and click 'Analyze Uploaded Resumes'.")

st.caption("LLM-powered candidate recommendations for uploaded resumes (confidence, strengths, weaknesses, and hiring advice).")
