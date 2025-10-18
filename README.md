AI-Powered Resume Screening Tool
A Streamlit web app for fast, objective, and scalable resume analysis and HR Q&A—powered by large language models (Groq API).

Features
AI screening for job fit: Upload PDF/DOCX resumes and paste a job description.

Instant candidate analysis: Each resume is scored for strengths, weaknesses, and fit.

Best-match highlighting: See the top candidate recommended for your role.

HR chat assistant: Instantly ask follow-up questions and compare candidates in human language.

Exportable results: Download all recommendations and analysis as a CSV.

Why This Removes Repetitive Manual Work
Automated parsing & analysis: Batch uploads let you scan dozens of resumes in seconds—no manual reading or ranking.

Structured scoring: Strengths, weaknesses, and recommendations appear instantly, eliminating manual scoring, ranking, and note-taking.

Batch comparison: Multiple resumes processed together, so you don’t need to review each one separately or copy-paste into spreadsheets.

Natural Q&A: Ask any HR question and get instant analysis without manually hunting through resumes or repeating the review process.

Easy export: Download results instantly—skip hours of generating reports by hand.

Result:
Recruiters, HR, and hiring managers focus on decisions instead of tedious review and repetitive resume screening.

Quick Start
Clone repo or upload to Streamlit Cloud

Install requirements:

bash
pip install streamlit pandas PyPDF2 docx2txt requests
Add your Groq API key as an environment variable or Streamlit secret:

Locally:

bash
export GROQ_API_KEY="sk-YOUR_API_KEY"
Streamlit Cloud:
Settings → Secrets → Add GROQ_API_KEY

Run:

bash
streamlit run app.py
How It Works
Upload resumes: PDF/DOCX, one or many.

Paste job description: All resume analysis is tailored to your job post.

Click Analyze Resumes: AI recommends the best fit, strengths, weaknesses, and suggests actions.

Ask follow-up HR Qs: Use the chat box for questions on candidates ("Who has best project experience?", "Who is weakest in ML?").

Get instant answers: The newest Q&A appears right below the chat box, with history below it.

Download CSV: Export all candidate recommendations and scores.

Example Questions for HR Chat
Who is the strongest candidate for Python?

Which candidate demonstrates leadership?

Main weaknesses across all applicants?

Should we shortlist Akash for technical interview?

Technology Stack
Python 3.9+

Streamlit (UI)

Groq LLM API (AI reasoning and candidate scoring)

pandas (table display)

PyPDF2, docx2txt (resume parsing)

Customization
Edit the prompt in build_candidate_prompt() for more targeted AI logic.

Change color/style in the CSS <style> block in app.py.

Rearrange chat layout in app.py for different Q&A history displays.

License
MIT License

Credits
Project by [Your Name]. Powered by Groq, Streamlit, and open-source libraries.