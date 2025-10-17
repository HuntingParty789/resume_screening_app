import os
import streamlit as st

# Dummy resume parser for demonstration (replace with real import/parsing code)
def batch_parse_resumes(folder):
    # Returns parsed resumes ("filename", "text"), hardcoded for illustration
    return [
        {"filename": "test_candidate_1.pdf", "text": "Alice Developer. B.Tech AI/ML. Python, GenAI tools."},
        {"filename": "test_candidate_2.pdf", "text": "Bob Engineer. M.Tech ML. Flask, FastAPI, Ollama."}
    ]

# Dummy JD parser
def parse_job_description(jd_text):
    return jd_text.strip()

# Diagnostic LLM prompt builder (remove all extraction for now)
def build_candidate_prompt(jd, resume_text):
    return f"{jd}\n{resume_text}\nSay 'Hello from the LLM'. Score: 99 Strengths: Demo Weaknesses: None"

# Minimal Groq LLM utility
import requests
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def call_llm(prompt):
    if not GROQ_API_KEY:
        st.error("Groq API key missing. Set GROQ_API_KEY as environment variable or .env.")
        return ""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        if not response.ok:
            st.error(f"Groq API error {response.status_code}: {response.text}")
            return ""
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"LLM call failed (API/network/config): {e}")
        return ""

st.set_page_config(page_title="Minimal LLM Test", layout="wide")
st.title("Minimal LLM Candidate Screening Test App")

job_desc = st.text_area("Enter job description:", height=100)

if st.button("Analyze Resumes"):
    resumes = batch_parse_resumes("data/resumes/")  # Replace with real parser
    st.write("DEBUG: parsed resumes", resumes)
    if not resumes:
        st.warning("No resumes found or parsing failed.")
    else:
        for res in resumes:
            st.info(f"Processing {res['filename']}")
            prompt = build_candidate_prompt(job_desc, res['text'])
            st.write(f"DEBUG: PROMPT sent to LLM =>", prompt)
            llm_result = call_llm(prompt)
            st.write(f"LLM RESPONSE for {res['filename']}:", llm_result if llm_result else "(BLANK/ERROR)")

else:
    st.info("Paste a job description and click ANALYZE to start.")

st.caption("If you **do not see an LLM RESPONSE** with 'Hello from the LLM' for each candidate, your LLM config/API key/model/connection is broken and needs fixing.")
