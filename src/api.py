from __future__ import annotations

import logging
import os
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .matcher import match_resume_to_jd
from .pdf_parser import extract_text_from_pdf
from .request_limits import RequestSizeLimitMiddleware

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 200_000
MAX_JOB_DESCRIPTION_BYTES = 200_000
MAX_MULTIPART_OVERHEAD_BYTES = 64 * 1024
MAX_REQUEST_BYTES = MAX_PDF_BYTES + MAX_JOB_DESCRIPTION_BYTES + MAX_MULTIPART_OVERHEAD_BYTES

app = FastAPI(title="AI Resume Screener API", version="1.0.0")
logger = logging.getLogger(__name__)
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if origin.strip()
]
# Register the body limit first so CORS wraps it and browser clients can read 413 responses.
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)
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
    if len(job_description.encode("utf-8")) > MAX_JOB_DESCRIPTION_BYTES:
        raise HTTPException(status_code=413, detail="Job description exceeds the 200 KB limit.")

    try:
        content = await resume.read(MAX_PDF_BYTES + 1)
    finally:
        await resume.close()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="Resume PDF must be 10 MB or smaller.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Upload a valid PDF resume.")

    try:
        resume_text = extract_text_from_pdf(content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.error("PDF extraction failed unexpectedly (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="The uploaded resume could not be processed.") from None
    if len(resume_text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=413, detail="The extracted resume text is too long to analyze.")

    try:
        score = match_resume_to_jd(resume_text, job_description)
    except Exception as error:
        logger.error("Resume matching failed unexpectedly (%s)", type(error).__name__)
        raise HTTPException(status_code=500, detail="Resume matching is temporarily unavailable.") from None
    return {"match_score": score, "status": "success"}
