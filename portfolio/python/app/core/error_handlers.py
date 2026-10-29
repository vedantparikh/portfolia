"""One JSON error body for every failed request."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.errors import DomainError, NotFoundError

logger = logging.getLogger(__name__)

_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    503: "unavailable",
}


def error_response(
    status_code: int,
    message: str,
    *,
    details: object = None,
    request: Request | None = None,
) -> JSONResponse:
    code = _CODES.get(status_code, f"http_{status_code}")
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    body: dict = {"error": error}
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


def _message(detail: object) -> str:
    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = [str(part) for part in item.get("loc", []) if part != "body"]
                msg = item.get("msg") or "Invalid value"
                parts.append(f"{'.'.join(loc)}: {msg}" if loc else str(msg))
            else:
                parts.append(str(item))
        if parts:
            return "; ".join(parts)
    if detail:
        return str(detail)
    return "Request failed"


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = 404 if isinstance(exc, NotFoundError) else 400
    return error_response(status_code, str(exc), request=request)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return error_response(exc.status_code, _message(exc.detail), request=request)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = jsonable_encoder(exc.errors())
    return error_response(422, _message(details), details=details, request=request)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled error on %s %s request_id=%s",
        request.method,
        request.url.path,
        getattr(request.state, "request_id", "-"),
    )
    return error_response(500, "Something went wrong", request=request)


def install_error_handlers(application: FastAPI) -> None:
    application.exception_handler(DomainError)(domain_error_handler)
    application.exception_handler(RequestValidationError)(validation_error_handler)
    application.exception_handler(StarletteHTTPException)(http_exception_handler)
    application.exception_handler(Exception)(unhandled_error_handler)
