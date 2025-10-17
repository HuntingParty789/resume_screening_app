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

job_desc = st.text_area("Enter the job description:", height=150)

if st.button("Analyze Resumes"):
    resumes = batch_parse_resumes("data/resumes/")
    if not resumes:
        st.warning("No resumes found or parsing failed. Please check the 'data/resumes/' folder and file formats.")
    else:
        jd_parsed = parse_job_description(job_desc)
        results = []
        table_data = []

        st.write("DEBUG: Parsed resumes", resumes)

        for res in resumes:
            st.info(f"Processing {res['filename']}")
            prompt = build_candidate_prompt(jd_parsed, res['text'])
            st.write(f"DEBUG: LLM prompt for {res['filename']}", prompt[:600])  # Show first 600 chars
            llm_result = call_llm(prompt)
            st.write(f"DEBUG: LLM result for {res['filename']}", llm_result[:600])
            results.append((res['filename'], llm_result, res['text']))

            # Try to extract score, strengths, weaknesses
            score_match = re.search(r"score\s*[:\-]?\s*(\d+)", llm_result, re.I)
            score = int(score_match.group(1)) if score_match else 0
            strengths = ""
            weaknesses = ""
            try:
                if "Strengths:" in llm_result:
                    strengths = llm_result.split("Strengths:")[1].split("Weaknesses:")[0].strip()
                if "Weaknesses:" in llm_result:
                    weaknesses = llm_result.split("Weaknesses:")[1].splitlines()[0].strip()
            except Exception as e:
                st.write(f"DEBUG: Strength/weakness parse error for {res['filename']} - {e}")

            table_data.append({
                "Filename": res['filename'],
                "Score": score,
                "Strengths": strengths,
                "Weaknesses": weaknesses,
                "LLM Result": llm_result,
                "Resume Text": res['text']
            })

        df = pd.DataFrame(table_data)
        st.write("DEBUG: Candidate DataFrame", df)

        # Filtering
        min_score = st.slider("Minimum Score Filter", 0, 100, 0)
        filtered_df = df[df["Score"] >= min_score].sort_values("Score", ascending=False)

        if filtered_df.empty:
            st.warning("No candidates meet the minimum score threshold.")
        else:
            st.subheader("Candidate Ranking Table")
            st.dataframe(filtered_df, use_container_width=True)

            # Downloads
            csv = filtered_df.to_csv(index=False)
            try:
                md_report = filtered_df.to_markdown(index=False)
            except Exception:
                md_report = "tabulate not installed; run 'pip install tabulate' and restart app."
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
                    st.markdown(row['Resume Text'][:1500])  # Only show first 1500 chars for brevity

            st.success(f"Analysis complete for {len(filtered_df)} candidate(s).")

            st.subheader("Ask about the Candidate Pool")
            question = st.text_input("Example: 'Who excels at Python?'")
            if question:
                if filtered_df.empty:
                    st.warning("No data for Q&A. Adjust score filter or check resume inputs.")
                else:
                    qna_context = "\n".join(f"Resume: {row['Filename']}\n{row['LLM Result']}" for _, row in filtered_df.iterrows())
                    full_prompt = f"Based on the following analyses:\n\n{qna_context}\n\nQuestion: {question}\nAnswer:"
                    with st.spinner("LLM answering your question..."):
                        qna_answer = call_llm(full_prompt)
                    st.markdown(f"**Q&A Result:** {qna_answer}")

else:
    st.info("Place resumes (PDF/DOCX) in the 'data/resumes/' folder and enter a job description to start analysis.")

st.caption("All results are LLM generated. Results may vary by prompt and candidate pool. © 2025")
