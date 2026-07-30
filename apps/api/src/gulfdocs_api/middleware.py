import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
logger = structlog.get_logger(__name__)


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    clear_contextvars()
    incoming_id = request.headers.get("x-request-id", "")
    request_id = incoming_id if _REQUEST_ID.fullmatch(incoming_id) else str(uuid4())
    bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    await logger.ainfo(
        "http_request_completed",
        status_code=response.status_code,
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )
    clear_contextvars()
    return response
