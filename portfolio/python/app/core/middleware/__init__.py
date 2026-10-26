"""One request id and one access line for every HTTP request."""

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def request_id_from(header: str | None) -> str:
    """Keep a caller-supplied id only when it cannot break the log line."""
    if header and _REQUEST_ID.fullmatch(header):
        return header
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request_id_from(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            _log_access(request, request_id, 500, started)
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        _log_access(request, request_id, response.status_code, started)
        return response


def _log_access(request: Request, request_id: str, status: int, started: float) -> None:
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "access method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        status,
        duration_ms,
        request_id,
    )
