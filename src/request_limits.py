"""Bound request bodies before multipart parsing can spool unbounded uploads."""

from tempfile import SpooledTemporaryFile

from starlette.responses import JSONResponse


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes: int, spool_memory_bytes: int = 64 * 1024):
        self.app = app
        self.max_bytes = max_bytes
        self.spool_memory_bytes = spool_memory_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/match" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                content_length = int(raw_length)
            except ValueError:
                await JSONResponse({"detail": "Invalid request size."}, status_code=400)(scope, receive, send)
                return
            if content_length < 0 or content_length > self.max_bytes:
                await self._payload_too_large(scope, receive, send)
                return

        body_file = SpooledTemporaryFile(max_size=self.spool_memory_bytes, mode="w+b")
        body_size = 0
        try:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue

                body = message.get("body", b"")
                body_size += len(body)
                if body_size > self.max_bytes:
                    await self._payload_too_large(scope, receive, send)
                    return
                body_file.write(body)
                if not message.get("more_body", False):
                    break

            body_file.seek(0)

            async def replay_body():
                chunk = body_file.read(64 * 1024)
                if not chunk:
                    return {"type": "http.disconnect"}
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": body_file.tell() < body_size,
                }

            await self.app(scope, replay_body, send)
        finally:
            body_file.close()

    async def _payload_too_large(self, scope, receive, send):
        response = JSONResponse(
            {"detail": "Request body exceeds the allowed size."},
            status_code=413,
        )
        await response(scope, receive, send)
