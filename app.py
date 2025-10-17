import os
import re
import pandas as pd
import streamlit as st
import requests

# ----------- CONFIGURE GROQ BELOW -----------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"   # <-- Replace with latest from https://console.groq.com/docs/deprecations if needed!

def call_llm(prompt):
    if not GROQ_API_KEY:
        st.error("Groq API key missing. Set GROQ_API_KEY as environment variable or .env.")
        return ""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400
    }
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        if not response.ok:
            st.error(f"Groq API error {response.status_code}:\n{response.text}")
            return ""
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"LLM call failed: {e}")
        return ""

# Dummy resume parser for demonstration — replace with your own!
def batch_parse_resumes(folder):
    return [
        {"filename": "test_candidate_1.pdf", "text": "Alice Developer. B.Tech AI/ML. Python, GenAI tools."},
        {"filename": "test_candidate_2.pdf", "text": "Bob Engineer. M.Tech ML. Flask, FastAPI, Ollama."}
    ]

def parse_job_description(jd_text):
    return jd_text.strip()

def build_candidate_prompt(jd, resume_text):
    return (
        f"Job Description:\n{jd}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        f"Score the candidate's fit (label as 'score:'). "
        f"List strengths (label 'Strengths:') and weaknesses (label 'Weaknesses:'). "
        f"Provide one short recommendation."
    )

st.set_page_config(page_title="LLM Screening App", layout="wide")
st.title("LLM-Powered Candidate Screening App")

job_desc = st.text_area("Enter the job description:", height=120)

if st.button("Analyze Resumes"):
    resumes = batch_parse_resumes("data/resumes/")  # Use your actual parser!
    st.write("DEBUG: parsed resumes", resumes)
    if not resumes:
        st.warning("No resumes found or parsing failed.")
    else:
        table_data = []
        for res in resumes:
            st.info(f"Processing {res['filename']}")
            prompt = build_candidate_prompt(job_desc, res['text'])
            st.write(f"DEBUG: LLM prompt for {res['filename']}", prompt)
            llm_result = call_llm(prompt)
            st.write(f"LLM response for {res['filename']}:", llm_result if llm_result else "(BLANK/ERROR)")

            score_match = re.search(r"score\s*[:\-]?\s*(\d+)", llm_result or "", re.I)
            score = int(score_match.group(1)) if score_match else 0
            strengths = ""
            weaknesses = ""
            try:
                if "Strengths:" in (llm_result or ""):
                    strengths = llm_result.split("Strengths:")[1].split("Weaknesses:")[0].strip()
                if "Weaknesses:" in (llm_result or ""):
                    weaknesses = llm_result.split("Weaknesses:")[1].splitlines()[0].strip()
            except Exception as e:
                st.write(f"DEBUG: Strength/weakness parse error for {res['filename']} - {e}")

            table_data.append({
                "Filename": res['filename'],
                "Score": score,
                "Strengths": strengths,
                "Weaknesses": weaknesses,
                "LLM Analysis": llm_result
            })

        df = pd.DataFrame(table_data)
        st.subheader("Candidate Ranking Table")
        min_score = st.slider("Minimum Score Filter", 0, 100, 0)
        filtered_df = df[df["Score"] >= min_score].sort_values("Score", ascending=False)
        st.dataframe(filtered_df, use_container_width=True)
        csv = filtered_df.to_csv(index=False)
        st.download_button("Download Results (CSV)", csv, file_name="screening_results.csv")

        st.subheader("Candidate Analysis Previews")
        for _, row in filtered_df.iterrows():
            with st.expander(f"{row['Filename']} - Analysis"):
                st.markdown(row['LLM Analysis'])

        st.success(f"Analysis complete for {len(filtered_df)} candidate(s).")

        st.subheader("Ask about the Candidate Pool")
        question = st.text_input("Example: 'Who excels at Python?'")
        if question and not filtered_df.empty:
            qna_context = "\n".join(
                f"Resume: {row['Filename']}\n{row['LLM Analysis']}" for _, row in filtered_df.iterrows()
            )
            full_prompt = f"Based on the following analyses:\n\n{qna_context}\n\nQuestion: {question}\nAnswer:"
            with st.spinner("LLM answering your question..."):
                qna_answer = call_llm(full_prompt)
            st.markdown(f"**Q&A Result:** {qna_answer}")

else:
    st.info("Place resumes (PDF/DOCX) in the 'data/resumes/' folder and enter a job description to start analysis.")

st.caption("Powered by Groq LLM. Results may vary by prompt and candidate pool.")
