import streamlit as st
import os

from parsing.resume_parser import batch_parse_resumes
from parsing.jd_parser import parse_job_description
from llm.prompts import build_candidate_prompt
from llm.llm_utils import call_llm

st.title("LLM-Powered Candidate Screening Application")

# Job description input
job_desc = st.text_area("Enter the job description:")

# Resume batch selection (expects resumes in data/resumes/)
if st.button("Analyze Resumes"):
    resumes = batch_parse_resumes("data/resumes/")
    jd_parsed = parse_job_description(job_desc)
    results = []

    for res in resumes:
        st.write(f"Processing {res['filename']}...")
        prompt = build_candidate_prompt(jd_parsed, res['text'])
        llm_result = call_llm(prompt)
        results.append((res['filename'], llm_result))
        st.markdown(f"**{res['filename']}**\n\n{llm_result}\n---")

    st.success("Analysis complete. See results above.")

st.info(
    "To run analysis, place resumes (PDF/DOCX) in the `data/resumes/` folder."
)
