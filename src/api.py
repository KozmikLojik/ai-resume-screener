from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from .pdf_parser import extract_text_from_pdf
from .matcher import match_resume_to_jd
import tempfile
import os

app = FastAPI(title="Resume Screener API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/match")
async def match_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    # Save uploaded resume temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await resume.read()
        tmp.write(content)
        tmp_path = tmp.name

    resume_text = extract_text_from_pdf(tmp_path)
    score = match_resume_to_jd(resume_text, job_description)

    os.unlink(tmp_path)  # Clean up

    return {"match_score": score, "status": "success"}