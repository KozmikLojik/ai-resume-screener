import unittest

from src.pdf_parser import extract_text_from_pdf
from src.pdf_parser import MAX_PDF_PAGES
from tests.pdf_fixtures import make_encrypted_pdf, make_multipage_pdf, make_pdf


class PdfParserTests(unittest.TestCase):
    def test_extracts_text_from_synthetic_pdf(self):
        self.assertIn("Python data analysis", extract_text_from_pdf(make_pdf()))

    def test_rejects_empty_bytes(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            extract_text_from_pdf(b"")

    def test_rejects_pdf_without_selectable_text(self):
        with self.assertRaisesRegex(ValueError, "No selectable text"):
            extract_text_from_pdf(make_pdf(text=""))

    def test_rejects_malformed_pdf(self):
        with self.assertRaisesRegex(ValueError, "not a readable PDF"):
            extract_text_from_pdf(b"%PDF-1.4\nnot a valid PDF structure")

    def test_rejects_encrypted_pdf_with_clear_message(self):
        with self.assertRaisesRegex(ValueError, "Encrypted PDFs are not supported"):
            extract_text_from_pdf(make_encrypted_pdf())

    def test_rejects_pdf_over_page_limit_before_extracting_all_pages(self):
        with self.assertRaisesRegex(ValueError, f"{MAX_PDF_PAGES} pages or fewer"):
            extract_text_from_pdf(make_multipage_pdf(MAX_PDF_PAGES + 1))


if __name__ == "__main__":
    unittest.main()
