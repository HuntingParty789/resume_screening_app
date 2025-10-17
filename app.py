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
    st.write("DEBUG: parsed resumes", resumes)

    if not resumes:
        st.warning("No resumes found or parsing failed. Please check the 'data/resumes/' folder and file formats.")
    else:
        jd_parsed = parse_job_description(job_desc)
        table_data = []

        for res in resumes:
            st.info(f"Processing {res['filename']}")
            prompt = build_candidate_prompt(jd_parsed, res['text'])
            st.write(f"DEBUG: LLM prompt for {res['filename']}", prompt[:500])  # Optional: show prompt for troubleshooting

            llm_result = call_llm(prompt)
            if not llm_result:
                st.error(f"LLM failed for {res['filename']}. Check API key/model or try again.")

            st.write(f"DEBUG: LLM result for {res['filename']}", llm_result[:500])
            score_match = re.search(r"score\s*[:\-]?\s*(\d+)", llm_result or "", re.I)
            score = int(score_match.group(1)) if score_match else 0
            strengths = ""
            weaknesses = ""
            if llm_result:
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
                "LLM Analysis": llm_result
            })

        df = pd.DataFrame(table_data)
        st.write("DEBUG: Candidate DataFrame", df)

        min_score = st.slider("Minimum Score Filter", 0, 100, 0)
        filtered_df = df[df["Score"] >= min_score].sort_values("Score", ascending=False)

        if filtered_df.empty:
            st.warning("No candidates meet the minimum score threshold.")
        else:
            st.subheader("Candidate Ranking Table")
            st.dataframe(filtered_df, use_container_width=True)
            csv = filtered_df.to_csv(index=False)
            try:
                md_report = filtered_df.to_markdown(index=False)
            except Exception:
                md_report = "tabulate not installed; run 'pip install tabulate'."
            st.download_button("Download CSV", csv, "screening_results.csv")
            st.download_button("Download Markdown", md_report, "screening_results.md")

            # Previews: Only LLM analysis!
            st.subheader("Candidate LLM Analysis Previews")
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

st.caption("All results are LLM generated. Results may vary by prompt, candidate pool, and LLM response quality. © 2025")
