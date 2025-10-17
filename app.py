import os
import re
import pandas as pd
import streamlit as st
import requests
from parsing.resume_parser import batch_parse_resumes

# Config Groq (update model if needed)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"

def call_llm(prompt):
    if not GROQ_API_KEY:
        st.error("Groq API key missing. Set GROQ_API_KEY!")
        return ""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.0   # <<<<< ENSURE DETERMINISTIC BEHAVIOR!
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

st.title("Best-fit Candidate Confidence Recommendations")

job_desc = st.text_area("Paste your job description", height=140)
if st.button("Analyze Resumes"):
    resumes = batch_parse_resumes("data/resumes/")
    if not resumes:
        st.warning("No PDF/DOCX resumes found in 'data/resumes/'.")
    else:
        results = []
        for res in resumes:
            prompt = build_candidate_prompt(job_desc, res['text'])
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
                "Filename": res['filename'],
                "Confidence": confidence,
                "Strengths": strengths,
                "Weaknesses": weaknesses,
                "Recommendation": recommendation
            })

        df = pd.DataFrame(results)
        # "High" sorts above "Medium" and "Low"
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
    st.info("Paste a job description, add resumes, and click 'Analyze Resumes'.")

st.caption("Confidence levels are LLM-AI generated and stabilized via low temperature, but may still vary slightly between runs.")
