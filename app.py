import re
import pandas as pd
import streamlit as st
import requests
import PyPDF2
import docx2txt
import tempfile
import os

# Groq Configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

def call_llm(prompt):
    """Call Groq LLM with error handling and retries"""
    if not GROQ_API_KEY:
        st.error("⚠️ Groq API key missing. Please set GROQ_API_KEY in your environment or Streamlit secrets.")
        return ""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 700,
        "temperature": 0.1  # Slight randomness for natural responses, but mostly deterministic
    }
    
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers, timeout=45)
        if not response.ok:
            st.error(f"🚫 Groq API error {response.status_code}: {response.text}")
            return ""
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. Please try again.")
        return ""
    except Exception as e:
        st.error(f"❌ LLM call failed: {str(e)}")
        return ""

def score_to_confidence(score):
    """Convert numeric score to confidence level with badges"""
    if score >= 85:
        return "🟢 High", "success"
    elif score >= 70:
        return "🟡 Medium", "warning"
    else:
        return "🔴 Low", "error"

def build_candidate_prompt(jd, resume_text):
    """Enhanced prompt for better LLM analysis"""
    return f"""You are an expert HR AI assistant specializing in candidate evaluation.

JOB DESCRIPTION:
{jd}

CANDIDATE RESUME:
{resume_text}

TASK: Provide a comprehensive assessment using this exact format:

score: [number between 0-100]
Strengths: [List 2-3 key strengths that align with the job requirements]
Weaknesses: [List 1-2 areas where the candidate may need improvement or doesn't fully match]
Recommendation: [One clear sentence: Should we hire, interview, or pass on this candidate and why?]

Be specific, professional, and focus on job-relevant qualifications. Ensure your score reflects the overall fit."""

def parse_pdf(file_bytes):
    """Parse PDF with better error handling"""
    try:
        reader = PyPDF2.PdfReader(file_bytes)
        if len(reader.pages) == 0:
            return "PDF appears to be empty or corrupted."
        text = " ".join([page.extract_text() or "" for page in reader.pages])
        return text.strip() if text.strip() else "Could not extract text from PDF."
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"

def parse_docx(file_bytes):
    """Parse DOCX with better error handling"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes.read())
            tmp.flush()
            text = docx2txt.process(tmp.name)
            os.unlink(tmp.name)  # Clean up temp file
        return text.strip() if text.strip() else "Could not extract text from DOCX."
    except Exception as e:
        return f"Error parsing DOCX: {str(e)}"

def parse_resume(filename, fileobj):
    """Parse resume based on file type"""
    fileobj.seek(0)  # Reset file pointer
    if filename.lower().endswith(".pdf"):
        return parse_pdf(fileobj)
    elif filename.lower().endswith(".docx"):
        return parse_docx(fileobj)
    else:
        return "❌ Unsupported file type. Please upload PDF or DOCX files."

# Streamlit App Configuration
st.set_page_config(
    page_title="AI Resume Screening Tool",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 2rem;
}
.candidate-card {
    background: #f8f9ff;
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 4px solid #667eea;
    margin: 1rem 0;
}
.stButton > button {
    width: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 25px;
    border: none;
    padding: 0.75rem;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="main-header">
    <h1>🎯 AI-Powered Resume Screening Tool</h1>
    <p>Upload resumes, get instant candidate recommendations with confidence levels</p>
</div>
""", unsafe_allow_html=True)

# Input Section
col1, col2 = st.columns([2, 1])

with col1:
    job_desc = st.text_area(
        "📋 Job Description",
        height=150,
        placeholder="Paste the complete job description here...",
        help="Include responsibilities, requirements, and desired qualifications"
    )

with col2:
    st.markdown("### 📁 Upload Guidelines")
    st.info("""
    • Support: PDF, DOCX files
    • Multiple files: Yes
    • Max size: 200MB per file
    • Best results: Clear, well-formatted resumes
    """)

# File Upload
uploaded_files = st.file_uploader(
    "📎 Upload Candidate Resumes",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    help="Select one or more resume files to analyze"
)

# Display uploaded files
if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} resume(s) uploaded successfully!")
    with st.expander("📋 Uploaded Files"):
        for file in uploaded_files:
            st.write(f"• {file.name} ({file.size/1024:.1f} KB)")

# Analysis Section
if st.button("🚀 Analyze Resumes", disabled=not (uploaded_files and job_desc.strip())):
    if not job_desc.strip():
        st.warning("⚠️ Please enter a job description first.")
    elif not uploaded_files:
        st.warning("⚠️ Please upload at least one resume.")
    else:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        total_files = len(uploaded_files)
        
        for idx, file in enumerate(uploaded_files):
            status_text.text(f"🔄 Processing {file.name}...")
            progress_bar.progress((idx + 1) / total_files)
            
            # Parse resume
            text = parse_resume(file.name, file)
            
            if text.startswith("Error") or text.startswith("❌"):
                results.append({
                    "Filename": file.name,
                    "Confidence": "❌ Error",
                    "Strengths": "File parsing failed",
                    "Weaknesses": text,
                    "Recommendation": "Unable to process this file"
                })
                continue
            
            # Get LLM analysis
            prompt = build_candidate_prompt(job_desc, text)
            llm_result = call_llm(prompt)
            
            if not llm_result:
                results.append({
                    "Filename": file.name,
                    "Confidence": "❌ Error",
                    "Strengths": "LLM analysis failed",
                    "Weaknesses": "Could not connect to AI service",
                    "Recommendation": "Please try again later"
                })
                continue
            
            # Extract information
            score_match = re.search(r"score\s*[:=\-]*\s*(\d+)", llm_result, re.I)
            score = int(score_match.group(1)) if score_match else 0
            confidence, badge_type = score_to_confidence(score)
            
            strengths = weaknesses = recommendation = ""
            try:
                strengths = re.search(r"Strengths:\s*(.*?)(?=Weaknesses:|Recommendation:|$)", llm_result, re.S).group(1).strip()
                weaknesses = re.search(r"Weaknesses:\s*(.*?)(?=Recommendation:|$)", llm_result, re.S).group(1).strip()
                recommendation = re.search(r"Recommendation:\s*(.*?)(?=\n\n|$)", llm_result, re.S).group(1).strip()
            except Exception:
                pass
            
            results.append({
                "Filename": file.name,
                "Confidence": confidence,
                "Strengths": strengths or "Not specified",
                "Weaknesses": weaknesses or "Not specified",
                "Recommendation": recommendation or "No recommendation provided"
            })
        
        progress_bar.empty()
        status_text.empty()
        
        # Display Results
        if results:
            df = pd.DataFrame(results)
            
            # Filter out errors for ranking
            valid_results = [r for r in results if not r["Confidence"].startswith("❌")]
            
            if valid_results:
                # Sort by confidence (High > Medium > Low)
                confidence_order = {"🟢 High": 3, "🟡 Medium": 2, "🔴 Low": 1}
                valid_df = pd.DataFrame(valid_results)
                valid_df['sort_order'] = valid_df['Confidence'].map(confidence_order)
                top_candidate = valid_df.sort_values('sort_order', ascending=False).iloc[0]
                
                # Top Recommendation
                st.markdown("## 🏆 Top Candidate Recommendation")
                st.markdown(f"""
                <div class="candidate-card">
                    <h3>📄 {top_candidate['Filename']}</h3>
                    <h4>Confidence Level: {top_candidate['Confidence']}</h4>
                    <p><strong>💪 Strengths:</strong> {top_candidate['Strengths']}</p>
                    <p><strong>⚠️ Areas for Improvement:</strong> {top_candidate['Weaknesses']}</p>
                    <p><strong>🎯 Recommendation:</strong> {top_candidate['Recommendation']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # All Results Table
            st.markdown("## 📊 All Candidates Summary")
            st.dataframe(
                df[["Filename", "Confidence", "Strengths", "Weaknesses", "Recommendation"]],
                use_container_width=True,
                hide_index=True
            )
            
            # Download Results
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download Detailed Results (CSV)",
                csv,
                file_name=f"candidate_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Analysis complete! Processed {len(results)} resume(s).")
        else:
            st.error("❌ No results generated. Please check your files and try again.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>🤖 Powered by Groq AI • Built with Streamlit</p>
    <p><small>Results are AI-generated recommendations for screening purposes only. Final hiring decisions should involve human review.</small></p>
</div>
""", unsafe_allow_html=True)
