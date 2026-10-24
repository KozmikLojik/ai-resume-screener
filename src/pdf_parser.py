from __future__ import annotations

import io

import pdfplumber
from PyPDF2 import PdfReader

MAX_PDF_PAGES = 100


class _RejectedPDF(Exception):
    """A valid-looking PDF that violates a supported input limit."""


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract selectable text from PDF bytes using two parser implementations."""
    if not pdf_content:
        raise ValueError("The uploaded PDF is empty.")

    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise _RejectedPDF(f"PDFs must contain {MAX_PDF_PAGES} pages or fewer.")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except _RejectedPDF as error:
        raise ValueError(str(error)) from None
    except Exception:
        try:
            reader = PdfReader(io.BytesIO(pdf_content), strict=False)
            if reader.is_encrypted:
                raise _RejectedPDF("Encrypted PDFs are not supported.")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise _RejectedPDF(f"PDFs must contain {MAX_PDF_PAGES} pages or fewer.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except _RejectedPDF as error:
            raise ValueError(str(error)) from None
        except Exception as error:
            raise ValueError("The uploaded file is not a readable PDF.") from error

    text = text.strip()
    if not text:
        raise ValueError("No selectable text was found in the PDF.")
    return text
