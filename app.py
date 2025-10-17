import os
import re
import pandas as pd
import streamlit as st

from parsing.resume_parser import batch_parse_resumes
from parsing.jd_parser import parse_job_description
from llm.prompts import build_candidate_prompt
from llm.llm_utils import call_llm

st.set_page_config(page_title="LLM Resume Screening", layout="wide")
st.title("LLM-Powered Candidate Screening App")

# Job Description Input
job_desc = st.text_area("Enter the job description:", height=150)

# Batch parse resumes if requested
if st.button("Analyze Resumes"):
    # Read resumes from folder
    resumes = batch_parse_resumes("data/resumes/")
    jd_parsed = parse_job_description(job_desc)
    results = []
    table_data = []

    for res in resumes:
        st.info(f"Processing {res['filename']}")
        prompt = build_candidate_prompt(jd_parsed, res['text'])
        llm_result = call_llm(prompt)
        results.append((res['filename'], llm_result, res['text']))
        
        # Score parsing example (tweak as per your prompt output format)
        score_match = re.search(r"score\s*[:\-]?\s*(\d+)", llm_result, re.I)
        score = int(score_match.group(1)) if score_match else 0
        strengths = llm_result.split("Strengths:")[1].split("Weaknesses:")[0].strip() if "Strengths:" in llm_result else ""
        weaknesses = llm_result.split("Weaknesses:")[1].strip() if "Weaknesses:" in llm_result else ""
        table_data.append({
            "Filename": res['filename'],
            "Score": score,
            "Strengths": strengths,
            "Weaknesses": weaknesses,
            "LLM Result": llm_result,
            "Resume Text": res['text']
        })

    # Table
    df = pd.DataFrame(table_data)
    st.subheader("Candidate Ranking Table")
    
    min_score = st.slider("Minimum Score Filter", 0, 100, 0)
    filtered_df = df[df["Score"] >= min_score].sort_values("Score", ascending=False)
    st.dataframe(filtered_df, use_container_width=True)

    # Download Buttons
    csv = filtered_df.to_csv(index=False)
    md_report = filtered_df.to_markdown(index=False)
    st.download_button("Download Results (CSV)", csv, file_name="screening_results.csv")
    st.download_button("Download Results (Markdown)", md_report, file_name="screening_results.md")

    # Resume Previews
    st.subheader("Resume Previews & LLM Analysis")
    for _, row in filtered_df.iterrows():
        with st.expander(f"{row['Filename']} - Preview"):
            st.markdown("**LLM analysis:**")
            st.markdown(row['LLM Result'])
            st.markdown("---")
            st.markdown("**Parsed Resume:**")
            st.markdown(row['Resume Text'])

    st.success(f"Analysis complete for {len(filtered_df)} candidate(s).")

    # Q&A Input
    st.subheader("Ask about the Candidate Pool")
    question = st.text_input("Example: 'Who excels at Python?'")
    if question:
        qna_context = "\n".join(f"Resume: {row['Filename']}\n{row['LLM Result']}" for _, row in filtered_df.iterrows())
        full_prompt = f"Based on the following analyses:\n\n{qna_context}\n\nQuestion: {question}\nAnswer:"
        qna_answer = call_llm(full_prompt)
        st.markdown(f"**Q&A Result:** {qna_answer}")

else:
    st.info("Place resumes (PDF/DOCX) in the `data/resumes/` folder and enter a job description to start analysis.")

st.caption("All results are LLM generated. Results may vary by prompt and candidate pool. © 2025")
