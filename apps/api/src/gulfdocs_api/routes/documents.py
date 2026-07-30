from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

import anyio
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from gulfdocs_document_intelligence.adapters.local import LocalFileStorage
from gulfdocs_document_intelligence.models import DocumentStatus
from gulfdocs_document_intelligence.repositories import DocumentRecord
from gulfdocs_persistence.repositories import SqlAlchemyDocumentRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..cloud_adapters import (
    CloudTasksQueueAdapter,
    DevelopmentTaskQueueAdapter,
    GcsSignedUploadAdapter,
    QueueConfiguration,
)
from ..config import Settings, get_settings
from ..dependencies import Authorized
from ..schemas import (
    CompleteUploadRequest,
    DocumentResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from ..upload_service import (
    capability_hash,
    inspect_pdf,
    store_bounded_pdf,
    upload_capability,
    verify_upload_capability,
)

router = APIRouter(prefix="/api/v1", tags=["documents"])


def _response(document: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        status=document.status.value,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        content_type=document.content_type,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _safe_filename(filename: str) -> str:
    if Path(filename).name != filename or not filename.casefold().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="A plain .pdf filename is required")
    if any(ord(character) < 32 for character in filename):
        raise HTTPException(status_code=422, detail="Filename contains invalid characters")
    return filename


def _presign_response(
    request: Request, document_id: UUID, expires_at: datetime, token: str
) -> PresignUploadResponse:
    upload_path = f"/api/v1/uploads/{document_id}/content?token={quote(token)}"
    return PresignUploadResponse(
        document_id=document_id,
        upload_url=str(request.base_url).rstrip("/") + upload_path,
        expires_at=expires_at,
        required_headers={"Content-Type": "application/pdf"},
    )


def _cloud_queue(settings: Settings) -> CloudTasksQueueAdapter | DevelopmentTaskQueueAdapter:
    if settings.task_queue_provider == "inline":
        return DevelopmentTaskQueueAdapter()
    if settings.task_queue_provider == "cloud_tasks":
        return CloudTasksQueueAdapter(
            QueueConfiguration(
                project_id=settings.gcp_project_id,
                region=settings.gcp_region,
                queue=settings.cloud_tasks_queue,
                worker_url=settings.cloud_tasks_worker_url,
                invoker_service_account=settings.cloud_tasks_invoker_service_account,
            )
        )
    raise RuntimeError(f"Unsupported task queue provider: {settings.task_queue_provider}")


@router.post("/uploads/presign", response_model=PresignUploadResponse, status_code=201)
async def presign_upload(
    payload: PresignUploadRequest,
    request: Request,
    context: Authorized,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> PresignUploadResponse:
    settings = get_settings()
    filename = _safe_filename(payload.filename)
    if payload.size_bytes > settings.max_pdf_size_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload size limit")
    repository = SqlAlchemyDocumentRepository(context.session)
    existing = await repository.find_upload_by_idempotency(
        context.identity.workspace_id, idempotency_key
    )
    if existing is not None:
        document, upload = existing
        token = upload_capability(
            settings.local_upload_signing_secret, document.id, upload.expires_at
        )
        if settings.storage_provider == "gcs":
            upload_url = await GcsSignedUploadAdapter(settings.gcs_bucket).create_upload_url(
                upload.object_key, upload.expires_at, "application/pdf"
            )
            return PresignUploadResponse(
                document_id=document.id,
                upload_url=upload_url,
                expires_at=upload.expires_at,
                required_headers={"Content-Type": "application/pdf"},
            )
        return _presign_response(request, document.id, upload.expires_at, token)
    allowed = await repository.consume_upload_allowance(
        context.identity, settings.max_uploads_per_user_per_day
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Daily upload limit reached")
    document_id = uuid4()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.upload_url_ttl_seconds)
    token = upload_capability(settings.local_upload_signing_secret, document_id, expires_at)
    object_key = f"{context.identity.workspace_id}/{document_id}/{uuid4()}.pdf"
    document, upload = await repository.create_pending_upload(
        identity=context.identity,
        filename=filename,
        expected_size_bytes=payload.size_bytes,
        idempotency_key=idempotency_key,
        token_hash=capability_hash(token),
        object_key=object_key,
        expires_at=expires_at,
        request_id=request.state.request_id,
        document_id=document_id,
    )
    if settings.storage_provider == "gcs":
        upload_url = await GcsSignedUploadAdapter(settings.gcs_bucket).create_upload_url(
            upload.object_key, upload.expires_at, "application/pdf"
        )
        return PresignUploadResponse(
            document_id=document.id,
            upload_url=upload_url,
            expires_at=upload.expires_at,
            required_headers={"Content-Type": "application/pdf"},
        )
    if settings.storage_provider != "local":
        raise RuntimeError(f"Unsupported storage provider: {settings.storage_provider}")
    return _presign_response(request, document.id, upload.expires_at, token)


@router.put("/uploads/{document_id}/content", status_code=204)
async def upload_content(document_id: UUID, token: str, request: Request) -> Response:
    settings = get_settings()
    if settings.storage_provider != "local":
        raise HTTPException(status_code=404, detail="Local upload adapter is disabled")
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        repository = SqlAlchemyDocumentRepository(session)
        row = await repository.get_upload_by_document(document_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Upload was not found")
        _, upload = row
        verify_upload_capability(settings.local_upload_signing_secret, upload, token)
        await store_bounded_pdf(
            request,
            upload=upload,
            storage=LocalFileStorage(Path(settings.local_storage_root)),
            max_size_bytes=settings.max_pdf_size_bytes,
        )
    return Response(status_code=204)


@router.post("/uploads/complete", response_model=DocumentResponse)
async def complete_upload(
    payload: CompleteUploadRequest, request: Request, context: Authorized
) -> DocumentResponse:
    settings = get_settings()
    repository = SqlAlchemyDocumentRepository(context.session)
    row = await repository.get_upload_for_workspace(
        context.identity.workspace_id, payload.document_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    _, upload = row
    temporary_cloud_path: Path | None = None
    try:
        if settings.storage_provider == "gcs":
            temporary_cloud_path = await GcsSignedUploadAdapter(
                settings.gcs_bucket
            ).download_to_temporary_path(upload.object_key)
            path = temporary_cloud_path
        elif settings.storage_provider == "local":
            path = await LocalFileStorage(Path(settings.local_storage_root)).get(upload.object_key)
        else:
            raise RuntimeError(f"Unsupported storage provider: {settings.storage_provider}")
        inspected = inspect_pdf(
            path,
            max_size_bytes=settings.max_pdf_size_bytes,
            max_pages=settings.max_document_pages,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail="Upload content has not been received") from exc
    finally:
        if temporary_cloud_path is not None:
            await anyio.Path(temporary_cloud_path).unlink(missing_ok=True)
    document = await repository.complete_upload(
        identity=context.identity,
        document_id=payload.document_id,
        storage_key=upload.object_key,
        content_sha256=inspected.sha256,
        size_bytes=inspected.size_bytes,
        page_count=inspected.page_count,
        request_id=request.state.request_id,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    if document.status is DocumentStatus.UPLOADED:
        queued = await repository.transition(
            identity=context.identity,
            document_id=document.id,
            target=DocumentStatus.QUEUED,
            request_id=request.state.request_id,
        )
        if queued is not None:
            document = queued
            queue = _cloud_queue(settings)
            task_id = await queue.enqueue_document(document.id, request.state.request_id)
            await repository.create_processing_run(
                document_id=document.id,
                task_id=task_id,
                correlation_id=request.state.request_id,
            )
    return _response(document)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    context: Authorized,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentResponse]:
    documents = await SqlAlchemyDocumentRepository(context.session).list_for_workspace(
        context.identity.workspace_id, limit, offset
    )
    return [_response(document) for document in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, context: Authorized) -> DocumentResponse:
    document = await SqlAlchemyDocumentRepository(context.session).get_for_workspace(
        context.identity.workspace_id, document_id
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    return _response(document)
