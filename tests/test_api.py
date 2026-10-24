import asyncio
import importlib
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from tests.pdf_fixtures import make_pdf


# Keep the pretrained model and heavyweight tensor runtime out of API tests.
_matcher_stub = types.ModuleType("src.matcher")
_matcher_stub.match_resume_to_jd = lambda _resume, _job: 0.0
_missing = object()
_previous_matcher = sys.modules.get("src.matcher", _missing)
sys.modules["src.matcher"] = _matcher_stub
try:
    api = importlib.import_module("src.api")
finally:
    if _previous_matcher is _missing:
        sys.modules.pop("src.matcher", None)
    else:
        sys.modules["src.matcher"] = _previous_matcher


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


def post_match(fields=None, files=(), include_content_length=True, chunk_size=None, origin=None):
    boundary, body = multipart(fields or {}, files)
    sent = []
    offset = 0

    async def receive():
        nonlocal offset
        if offset >= len(body):
            return {"type": "http.disconnect"}
        size = chunk_size or len(body)
        chunk = body[offset:offset + size]
        offset += len(chunk)
        return {"type": "http.request", "body": chunk, "more_body": offset < len(body)}

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
        "headers": [(b"content-type", f"multipart/form-data; boundary={boundary}".encode())]
        + ([(b"content-length", str(len(body)).encode())] if include_content_length else [])
        + ([(b"origin", origin.encode())] if origin else []),
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

    def test_missing_job_description_returns_bad_request(self):
        status, body = post_match(files=[("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertEqual(body["detail"], "A job description is required.")

    def test_empty_job_description_returns_bad_request(self):
        status, body = post_match({"job_description": ""}, [("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertEqual(body["detail"], "A job description is required.")

    def test_whitespace_job_description_returns_bad_request(self):
        status, body = post_match({"job_description": "   "}, [("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertIn("required", body["detail"])

    def test_non_pdf_upload_returns_bad_request(self):
        status, body = post_match(
            {"job_description": "Python developer"}, [("resume", "candidate.pdf", "application/pdf", b"not a PDF")]
        )
        self.assertEqual(status, 400)
        self.assertIn("valid PDF", body["detail"])

    def test_empty_upload_returns_bad_request(self):
        status, body = post_match({"job_description": "Python developer"}, [("resume", "empty.pdf", "application/pdf", b"")])
        self.assertEqual(status, 400)
        self.assertIn("valid PDF", body["detail"])

    def test_uploads_below_and_at_file_limit_are_accepted(self):
        with patch.object(api, "extract_text_from_pdf", return_value="Synthetic resume text"), patch.object(
            api, "match_resume_to_jd", return_value=50.0
        ):
            for size in (api.MAX_PDF_BYTES - 1, api.MAX_PDF_BYTES):
                with self.subTest(size=size):
                    payload = b"%PDF-" + b"x" * (size - 5)
                    status, _ = post_match(
                        {"job_description": "Python developer"},
                        [("resume", "resume.pdf", "application/pdf", payload)],
                    )
                    self.assertEqual(status, 200)

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

    def test_oversized_job_description_is_rejected(self):
        status, body = post_match(
            {"job_description": "x" * (api.MAX_JOB_DESCRIPTION_BYTES + 1)},
            [("resume", *self.valid_file)],
        )
        self.assertEqual(status, 413)
        self.assertIn("200 KB", body["detail"])

    def test_job_description_limit_counts_utf8_bytes(self):
        description = "é" * (api.MAX_JOB_DESCRIPTION_BYTES // 2)
        self.assertEqual(len(description.encode("utf-8")), api.MAX_JOB_DESCRIPTION_BYTES)
        with patch.object(api, "extract_text_from_pdf", return_value="Synthetic resume text"), patch.object(
            api, "match_resume_to_jd", return_value=50.0
        ):
            status, _ = post_match({"job_description": description}, [("resume", *self.valid_file)])
        self.assertEqual(status, 200)

    def test_chunked_request_over_total_limit_is_rejected_with_cors(self):
        with patch.object(api, "extract_text_from_pdf") as parser:
            status, body = post_match(
                {"job_description": "x" * api.MAX_REQUEST_BYTES},
                include_content_length=False,
                chunk_size=64 * 1024,
                origin="http://localhost:8501",
            )
        self.assertEqual(status, 413)
        self.assertIn("allowed size", body["detail"])
        parser.assert_not_called()

    def test_request_spool_is_closed_after_processing(self):
        spool = tempfile.SpooledTemporaryFile()
        messages = [{"type": "http.request", "body": b"abc", "more_body": False}]
        sent = []

        async def receive():
            return messages.pop(0) if messages else {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        async def downstream(scope, receive_body, send_response):
            await receive_body()
            await send_response({"type": "http.response.start", "status": 200, "headers": []})
            await send_response({"type": "http.response.body", "body": b"ok"})

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/match",
            "headers": [(b"content-length", b"3")],
        }
        middleware = api.RequestSizeLimitMiddleware(downstream, max_bytes=100)
        with patch("src.request_limits.SpooledTemporaryFile", return_value=spool) as spool_factory:
            asyncio.run(middleware(scope, receive, send))
        self.assertEqual(spool_factory.call_count, 1)
        self.assertTrue(spool.closed)
        self.assertEqual(sent[0]["status"], 200)

    def test_parser_value_error_is_a_client_error(self):
        with patch.object(api, "extract_text_from_pdf", side_effect=ValueError("No selectable text was found in the PDF.")):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 400)
        self.assertIn("No selectable text", body["detail"])

    def test_unexpected_parser_error_is_sanitized(self):
        with self.assertLogs(api.__name__, level="ERROR") as captured, patch.object(
            api, "extract_text_from_pdf", side_effect=RuntimeError("SENSITIVE_RESUME_TEXT")
        ):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 500)
        self.assertEqual(body["detail"], "The uploaded resume could not be processed.")
        self.assertNotIn("SENSITIVE_RESUME_TEXT", json.dumps(body) + "\n".join(captured.output))
        self.assertIn("RuntimeError", "\n".join(captured.output))

    def test_unexpected_matcher_error_is_sanitized(self):
        with self.assertLogs(api.__name__, level="ERROR") as captured, patch.object(
            api, "extract_text_from_pdf", return_value="SENSITIVE_RESUME_TEXT"
        ), patch.object(api, "match_resume_to_jd", side_effect=RuntimeError("SENSITIVE_JOB_DESCRIPTION")):
            status, body = post_match({"job_description": "Python developer"}, [("resume", *self.valid_file)])
        self.assertEqual(status, 500)
        self.assertEqual(body["detail"], "Resume matching is temporarily unavailable.")
        logged = "\n".join(captured.output)
        self.assertNotIn("SENSITIVE_RESUME_TEXT", json.dumps(body) + logged)
        self.assertNotIn("SENSITIVE_JOB_DESCRIPTION", json.dumps(body) + logged)
        self.assertIn("RuntimeError", logged)


if __name__ == "__main__":
    unittest.main()
