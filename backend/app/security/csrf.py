"""CSRF protection for state-changing API requests.

The frontend calls the API same-origin (Next.js proxies /api), and the backend
enables no CORS. A cross-site page therefore cannot attach the custom header
below without a preflight that the backend never approves. If an Origin header
is present it must also be an allowed origin.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import error_body

CSRF_HEADER = "x-atlas-csrf"
_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origins: list[str]) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._allowed = {o.rstrip("/") for o in allowed_origins}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _UNSAFE and request.url.path.startswith("/api/"):
            if request.headers.get(CSRF_HEADER) != "1":
                return JSONResponse(error_body("csrf_failed", "Missing CSRF header."), status_code=403)
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") not in self._allowed:
                return JSONResponse(
                    error_body("csrf_failed", "Request origin is not allowed."), status_code=403
                )
        return await call_next(request)
