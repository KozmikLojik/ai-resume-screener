import unittest

from src.pdf_parser import extract_text_from_pdf
from tests.pdf_fixtures import make_pdf


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


if __name__ == "__main__":
    unittest.main()
