import os
import PyPDF2
import docx2txt

def parse_pdf(file_path):
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = " ".join(page.extract_text() or "" for page in reader.pages)
    return text

def parse_docx(file_path):
    return docx2txt.process(file_path)

def parse_resume(file_path):
    if file_path.endswith(".pdf"):
        return parse_pdf(file_path)
    elif file_path.endswith(".docx"):
        return parse_docx(file_path)
    else:
        raise ValueError("Unsupported file type")

def batch_parse_resumes(folder):
    resumes = []
    for fname in os.listdir(folder):
        full_path = os.path.join(folder, fname)
        if fname.lower().endswith((".pdf", ".docx")):
            text = parse_resume(full_path)
            resumes.append({"filename": fname, "text": text})
    return resumes
