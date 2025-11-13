import pdfplumber
import PyPDF2
from typing import List

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber (better than PyPDF2)"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        return text.strip()
    except:
        # Fallback
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()