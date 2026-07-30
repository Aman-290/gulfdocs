from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from gulfdocs_persistence.database import create_engine, create_session_factory
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth import build_token_verifier
from .config import get_settings
from .logging import configure_logging
from .middleware import request_context_middleware
from .routes.demo import router as demo_router
from .routes.documents import router as documents_router
from .schemas import HealthResponse, ProblemDetail

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.app_env not in {"development", "test"} and (
        settings.storage_provider == "local" or settings.task_queue_provider == "inline"
    ):
        raise RuntimeError("Local storage and inline queues are forbidden outside development/test")
    engine = create_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.token_verifier = build_token_verifier(settings)
    app.state.ready = True
    await logger.ainfo("service_started", service="gulfdocs-api", environment=settings.app_env)
    yield
    app.state.ready = False
    await engine.dispose()
    await logger.ainfo("service_stopped", service="gulfdocs-api")


app = FastAPI(
    title="GulfDocs API",
    version="0.1.0",
    description="Authorized document workflows and a bounded, synthetic public demo.",
    lifespan=lifespan,
)
app.middleware("http")(request_context_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
if settings.public_demo_enabled:
    app.include_router(demo_router)
app.include_router(documents_router)


def problem_response(request: Request, status_code: int, title: str, detail: str) -> JSONResponse:
    error_id = str(uuid4())
    request_id = getattr(request.state, "request_id", error_id)
    body = ProblemDetail(
        title=title,
        status=status_code,
        detail=detail,
        error_id=error_id,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        media_type="application/problem+json",
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return problem_response(request, exc.status_code, "Request failed", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    del exc
    return problem_response(
        request, 422, "Validation failed", "The request did not match the expected schema."
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    await logger.aexception("unhandled_request_error", exception_type=type(exc).__name__)
    return problem_response(
        request, 500, "Internal server error", "The request could not be completed."
    )


@app.get("/healthz", response_model=HealthResponse, tags=["operations"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="gulfdocs-api", version=app.version)


@app.get("/readyz", response_model=HealthResponse, tags=["operations"])
async def readiness(request: Request) -> HealthResponse:
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Service is not ready")
    try:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return HealthResponse(status="ready", service="gulfdocs-api", version=app.version)
