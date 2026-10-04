from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .matcher import match_resume_to_jd
from .pdf_parser import extract_text_from_pdf

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 200_000

app = FastAPI(title="AI Resume Screener API", version="1.0.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/match")
async def match_resume(
    resume: Annotated[UploadFile, File(...)],
    job_description: Annotated[str, Form(...)],
) -> dict[str, float | str]:
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="A job description is required.")

    content = await resume.read(MAX_PDF_BYTES + 1)
    await resume.close()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="Resume PDF must be 10 MB or smaller.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Upload a valid PDF resume.")

    try:
        resume_text = extract_text_from_pdf(content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if len(resume_text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=413, detail="The extracted resume text is too long to analyze.")

    score = match_resume_to_jd(resume_text, job_description)
    return {"match_score": score, "status": "success"}
