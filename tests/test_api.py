import asyncio
import importlib
import json
import sys
import types
import unittest
from unittest.mock import patch

from tests.pdf_fixtures import make_pdf


# Keep the pretrained model and heavyweight tensor runtime out of API tests.
_matcher_stub = types.ModuleType("src.matcher")
_matcher_stub.match_resume_to_jd = lambda _resume, _job: 0.0
with patch.dict(sys.modules, {"src.matcher": _matcher_stub}):
    api = importlib.import_module("src.api")


def multipart(fields, files=()):
    boundary = "resume-screener-test-boundary"
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode(),
            value.encode(),
            b"\r\n",
        ])
    for name, filename, content_type, value in files:
        chunks.extend([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(),
            value,
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def post_match(fields=None, files=()):
    boundary, body = multipart(fields or {}, files)
    sent = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/match",
        "raw_path": b"/match",
        "query_string": b"",
        "headers": [(b"content-type", f"multipart/form-data; boundary={boundary}".encode())],
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
    }
    asyncio.run(api.app(scope, receive, send))
    response_start = next(message for message in sent if message["type"] == "http.response.start")
    response_body = next(message for message in sent if message["type"] == "http.response.body")["body"]
    return response_start["status"], json.loads(response_body or b"{}")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.valid_file = ("resume.pdf", "application/pdf", make_pdf())

    def test_success_returns_score_and_status(self):
        with patch.object(api, "extract_text_from_pdf", return_value="Synthetic resume text"), patch.object(
            api, "match_resume_to_jd", return_value=73.5
        ):
            status, body = post_match({"job_description": "Synthetic job description"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 200)
        self.assertEqual(body, {"match_score": 73.5, "status": "success"})

    def test_missing_resume_returns_validation_error(self):
        status, body = post_match({"job_description": "Python developer"})
        self.assertEqual(status, 422)
        self.assertIn("detail", body)

    def test_missing_job_description_returns_validation_error(self):
        status, body = post_match(files=[("resume", *self.valid_file)])
        self.assertEqual(status, 422)
        self.assertIn("detail", body)

    def test_empty_job_description_returns_bad_request(self):
        status, body = post_match({"job_description": "   "}, [("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertIn("required", body["detail"])

    def test_non_pdf_upload_returns_bad_request(self):
        status, body = post_match(
            {"job_description": "Python developer"}, [("resume", "resume.docx", "application/pdf", b"not a PDF")]
        )
        self.assertEqual(status, 400)
        self.assertIn("valid PDF", body["detail"])

    def test_oversized_upload_returns_payload_too_large(self):
        oversized = b"%PDF-" + b"x" * api.MAX_PDF_BYTES
        status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file[:2], oversized)])
        self.assertEqual(status, 413)
        self.assertIn("10 MB", body["detail"])

    def test_extracted_text_over_limit_returns_payload_too_large(self):
        with patch.object(api, "extract_text_from_pdf", return_value="x" * (api.MAX_TEXT_LENGTH + 1)), patch.object(
            api, "match_resume_to_jd"
        ) as matcher:
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 413)
        self.assertIn("too long", body["detail"])
        matcher.assert_not_called()

    def test_parser_value_error_is_a_client_error(self):
        with patch.object(api, "extract_text_from_pdf", side_effect=ValueError("No selectable text was found in the PDF.")):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertIn("No selectable text", body["detail"])

    def test_unexpected_parser_error_is_sanitized(self):
        with patch.object(api, "extract_text_from_pdf", side_effect=RuntimeError("private parser detail")):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 500)
        self.assertEqual(body["detail"], "The uploaded resume could not be processed.")
        self.assertNotIn("private parser detail", json.dumps(body))

    def test_unexpected_matcher_error_is_sanitized(self):
        with patch.object(api, "extract_text_from_pdf", return_value="Synthetic resume text"), patch.object(
            api, "match_resume_to_jd", side_effect=RuntimeError("private matching detail")
        ):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 500)
        self.assertEqual(body["detail"], "Resume matching is temporarily unavailable.")
        self.assertNotIn("private matching detail", json.dumps(body))


if __name__ == "__main__":
    unittest.main()
