from __future__ import annotations

import io

import pdfplumber
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract selectable text from PDF bytes using two parser implementations."""
    if not pdf_content:
        raise ValueError("The uploaded PDF is empty.")

    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        try:
            reader = PdfReader(io.BytesIO(pdf_content), strict=False)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            raise ValueError("The uploaded file is not a readable PDF.") from error

    text = text.strip()
    if not text:
        raise ValueError("No selectable text was found in the PDF.")
    return text
