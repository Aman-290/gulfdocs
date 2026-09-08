from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import anyio
import structlog
from google.api_core.exceptions import NotFound
from google.cloud import storage  # type: ignore[attr-defined]
from gulfdocs_document_intelligence.adapters import LocalFileStorage
from gulfdocs_document_intelligence.models import DocumentStatus
from gulfdocs_persistence.database import create_engine, create_session_factory
from gulfdocs_persistence.models import (
    AuditEvent,
    Document,
    DocumentAnswer,
    DocumentChunk,
    DocumentPage,
    DocumentQuestion,
    DocumentReview,
    DocumentUpload,
    ExtractedResult,
    ExtractionField,
    ExtractionRevision,
    ValidationIssue,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import WorkerSettings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RetentionOutcome:
    purged_documents: int
    failed_documents: int


class RetentionCleanup:
    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings

    async def run(self) -> RetentionOutcome:
        cutoff = datetime.now(UTC) - timedelta(days=self.settings.document_retention_days)
        engine = create_engine(self.settings.database_url)
        sessions = create_session_factory(engine)
        purged = 0
        failed = 0
        try:
            async with sessions.begin() as session:
                documents = list(
                    await session.scalars(
                        select(Document)
                        .where(
                            Document.updated_at < cutoff,
                            Document.status.not_in(
                                (
                                    DocumentStatus.PENDING_UPLOAD.value,
                                    DocumentStatus.QUEUED.value,
                                    DocumentStatus.VALIDATING.value,
                                    DocumentStatus.EXTRACTING.value,
                                    DocumentStatus.INDEXING.value,
                                    DocumentStatus.DELETED.value,
                                )
                            ),
                        )
                        .order_by(Document.updated_at)
                        .limit(self.settings.retention_cleanup_batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                for document in documents:
                    try:
                        await self._delete_object(document.storage_key)
                        async with session.begin_nested():
                            await self._purge_content(session, document)
                        purged += 1
                    except Exception as exc:
                        failed += 1
                        await logger.aerror(
                            "retention_document_failed",
                            document_id=str(document.id),
                            exception_type=type(exc).__name__,
                        )
        finally:
            await engine.dispose()
        return RetentionOutcome(purged_documents=purged, failed_documents=failed)

    async def _delete_object(self, object_key: str | None) -> None:
        if not object_key:
            return
        if self.settings.storage_provider == "local":
            await LocalFileStorage(Path(self.settings.local_storage_root)).delete(object_key)
            return
        if self.settings.storage_provider == "gcs":
            bucket = storage.Client(project=self.settings.gcp_project_id).bucket(
                self.settings.gcs_bucket
            )
            try:
                await anyio.to_thread.run_sync(bucket.blob(object_key).delete)
            except NotFound:
                return
            return
        raise RuntimeError(f"Unsupported storage provider: {self.settings.storage_provider}")

    async def _purge_content(self, session: AsyncSession, document: Document) -> None:
        result_ids = select(ExtractedResult.id).where(ExtractedResult.document_id == document.id)
        field_ids = select(ExtractionField.id).where(ExtractionField.result_id.in_(result_ids))
        question_ids = select(DocumentQuestion.id).where(
            DocumentQuestion.document_id == document.id
        )
        for statement in (
            delete(ExtractionRevision).where(ExtractionRevision.field_id.in_(field_ids)),
            delete(ExtractionField).where(ExtractionField.result_id.in_(result_ids)),
            delete(ValidationIssue).where(ValidationIssue.document_id == document.id),
            delete(DocumentReview).where(DocumentReview.document_id == document.id),
            delete(DocumentAnswer).where(DocumentAnswer.question_id.in_(question_ids)),
            delete(DocumentQuestion).where(DocumentQuestion.document_id == document.id),
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id),
            delete(DocumentPage).where(DocumentPage.document_id == document.id),
            delete(ExtractedResult).where(ExtractedResult.document_id == document.id),
            delete(DocumentUpload).where(DocumentUpload.document_id == document.id),
        ):
            await session.execute(statement)
        document.safe_display_name = "retention-purged.pdf"
        document.original_filename = "retention-purged.pdf"
        document.storage_key = None
        document.content_sha256 = None
        document.content_type = None
        document.size_bytes = None
        document.page_count = None
        document.document_type = None
        document.detected_language = None
        document.failure_category = None
        document.status = DocumentStatus.DELETED.value
        document.deleted_at = datetime.now(UTC)
        document.updated_at = datetime.now(UTC)
        session.add(
            AuditEvent(
                event_type="retention_purged",
                actor_id=None,
                workspace_id=document.workspace_id,
                document_id=document.id,
                request_id=f"retention-{document.id}",
                safe_metadata={"policy_days": self.settings.document_retention_days},
            )
        )
