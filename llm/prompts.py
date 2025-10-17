def build_candidate_prompt(jd, resume_text):
    return (
        f"Job Description:\n{jd}\n\n"
        f"Candidate Resume:\n{resume_text}\n\n"
        f"Analyze how closely the candidate matches the job, "
        f"their strengths and weaknesses, and provide a fit score (0-100) with explanation."
    )
