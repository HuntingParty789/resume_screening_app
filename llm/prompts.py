def build_candidate_prompt(jd, resume_text):
    return (
        f"Job Description:\n{jd}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        f"Analyze the candidate's fit for the job description. "
        f"Provide:\n- A match score (0-100, label 'score:')\n- Strengths (label 'Strengths:')\n- Weaknesses (label 'Weaknesses:')\n"
        f"Summarize their match, strengths, weaknesses, and overall recommendation."
    )
