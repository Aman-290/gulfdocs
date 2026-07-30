import logging
import secrets
import sys
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .config import WorkerSettings, get_worker_settings


def configure_logging(level: str) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper())
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class ProcessDocumentTask(BaseModel):
    document_id: UUID
    processing_run_id: UUID
    correlation_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    attempt: int = Field(default=1, ge=1, le=10)


class TaskResult(BaseModel):
    status: str
    document_id: UUID
    processing_run_id: UUID
    idempotent_replay: bool


settings = get_worker_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)
app = FastAPI(
    title="GulfDocs private worker",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
_completed_runs: set[UUID] = set()


async def require_worker_identity(
    worker_settings: Annotated[WorkerSettings, Depends(get_worker_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if worker_settings.worker_auth_mode != "development":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud OIDC verification is not configured",
        )
    expected = f"Bearer {worker_settings.worker_development_token}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Worker authentication required"
        )


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gulfdocs-worker", "version": app.version}


@app.post(
    "/internal/tasks/process-document",
    response_model=TaskResult,
    dependencies=[Depends(require_worker_identity)],
)
async def process_document(task: ProcessDocumentTask) -> TaskResult:
    replay = task.processing_run_id in _completed_runs
    if not replay:
        # The deterministic pipeline and persistent lock arrive in Phase 3. This local
        # equivalent proves authenticated, identifier-only, idempotent task delivery.
        _completed_runs.add(task.processing_run_id)
        await logger.ainfo(
            "local_document_task_processed",
            document_id=str(task.document_id),
            processing_run_id=str(task.processing_run_id),
            correlation_id=task.correlation_id,
            attempt=task.attempt,
        )
    return TaskResult(
        status="already_processed" if replay else "processed",
        document_id=task.document_id,
        processing_run_id=task.processing_run_id,
        idempotent_replay=replay,
    )
