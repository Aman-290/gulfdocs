import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from uuid import UUID

import anyio
from google.cloud import storage  # type: ignore[attr-defined]
from gulfdocs_document_intelligence.adapters import LocalFileStorage
from gulfdocs_document_intelligence.chunking import chunk_pages
from gulfdocs_document_intelligence.models import DocumentStatus
from gulfdocs_document_intelligence.parsing import document_language, parse_pdf_pages
from gulfdocs_document_intelligence.providers import AIProvider, FakeAIProvider, GeminiProvider
from gulfdocs_document_intelligence.status_machine import require_legal_transition
from gulfdocs_document_intelligence.validation import DeterministicIssue
from gulfdocs_document_intelligence.workflow import DeterministicDocumentWorkflow
from gulfdocs_persistence.database import create_engine, create_session_factory
from gulfdocs_persistence.models import (
    AuditEvent,
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentProcessingRun,
    ExtractedResult,
    ExtractionField,
    SecurityEvent,
    ValidationIssue,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import WorkerSettings

PARSER_VERSION = "pymupdf-1"
PROMPT_VERSION = "gulfdocs-extraction-1"


@dataclass(frozen=True, slots=True)
class ProcessingTask:
    document_id: UUID
    processing_run_id: UUID
    correlation_id: str
    attempt: int


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    status: str
    idempotent_replay: bool


class PersistentDocumentProcessor:
    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        if settings.ai_provider == "fake":
            self.provider: AIProvider = FakeAIProvider()
        elif settings.ai_provider == "gemini":
            self.provider = GeminiProvider(
                model_name=settings.gemini_extraction_model,
                embedding_model=settings.gemini_embedding_model,
                api_key=settings.gemini_api_key,
                project=settings.gcp_project_id or None,
                location=settings.gcp_region,
            )
        else:
            raise RuntimeError(f"Unsupported AI provider: {settings.ai_provider}")

    async def process(self, task: ProcessingTask) -> ProcessingOutcome:
        engine = create_engine(self.settings.database_url)
        sessions = create_session_factory(engine)
        started = monotonic()
        temporary_path: Path | None = None
        try:
            async with sessions.begin() as session:
                row = (
                    await session.execute(
                        select(DocumentProcessingRun, Document)
                        .join(Document, Document.id == DocumentProcessingRun.document_id)
                        .where(
                            DocumentProcessingRun.id == task.processing_run_id,
                            Document.id == task.document_id,
                        )
                        .with_for_update()
                    )
                ).first()
                if row is None:
                    raise LookupError("Document processing run was not found")
                run, document = row
                if run.status == "completed":
                    return ProcessingOutcome("already_processed", True)
                if run.status == "running":
                    return ProcessingOutcome("already_processing", True)
                if run.attempt != task.attempt or document.status != DocumentStatus.QUEUED.value:
                    raise ValueError("Task identifiers do not match the queued processing state")
                require_legal_transition(DocumentStatus(document.status), DocumentStatus.VALIDATING)
                document.status = DocumentStatus.VALIDATING.value
                run.status = "running"
                run.started_at = datetime.now(UTC)
                session.add(
                    AuditEvent(
                        event_type="processing_started",
                        actor_id=None,
                        workspace_id=document.workspace_id,
                        document_id=document.id,
                        request_id=task.correlation_id,
                        safe_metadata={"processing_run_id": str(run.id), "attempt": run.attempt},
                    )
                )

            path, temporary_path = await self._document_path(document)
            pages = parse_pdf_pages(path)
            workflow = await DeterministicDocumentWorkflow(self.provider).run(
                [page.text for page in pages]
            )
            chunks = chunk_pages(pages)
            embeddings = await self.provider.embed([chunk.text for chunk in chunks])

            async with sessions.begin() as session:
                row = (
                    await session.execute(
                        select(DocumentProcessingRun, Document)
                        .join(Document, Document.id == DocumentProcessingRun.document_id)
                        .where(DocumentProcessingRun.id == task.processing_run_id)
                        .with_for_update()
                    )
                ).one()
                run, document = row
                if run.status == "completed":
                    return ProcessingOutcome("already_processed", True)
                extraction = workflow["extraction"]
                issues = workflow["issues"]
                signals = workflow["security_signals"]
                identifier = extraction.fields.get("document_number")
                if identifier and isinstance(identifier.value, str):
                    duplicate = await session.scalar(
                        select(Document.id)
                        .join(ExtractedResult, ExtractedResult.document_id == Document.id)
                        .join(ExtractionField, ExtractionField.result_id == ExtractedResult.id)
                        .where(
                            Document.workspace_id == document.workspace_id,
                            Document.id != document.id,
                            ExtractionField.field_key == "document_number",
                            ExtractionField.value["value"].astext == identifier.value,
                        )
                        .limit(1)
                    )
                    if duplicate is not None:
                        issues.append(
                            DeterministicIssue(
                                code="DUPLICATE_DOCUMENT_NUMBER",
                                severity="critical",
                                description="This document number already exists in the workspace.",
                                related_fields=("document_number",),
                                source_page=(
                                    identifier.citations[0].page if identifier.citations else None
                                ),
                                suggested_action="Confirm whether this is a duplicate document.",
                            )
                        )
                await session.execute(
                    delete(DocumentPage).where(DocumentPage.document_id == document.id)
                )
                await session.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
                )
                for page in pages:
                    session.add(
                        DocumentPage(
                            document_id=document.id,
                            page_number=page.page_number,
                            text=page.text,
                            detected_language=page.detected_language,
                            parser_confidence=Decimal("1.0000") if page.text else Decimal("0.0000"),
                        )
                    )
                for chunk, embedding in zip(chunks, embeddings, strict=True):
                    session.add(
                        DocumentChunk(
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            page_number=chunk.page_number,
                            chunk_text=chunk.text,
                            detected_language=chunk.detected_language,
                            token_count=chunk.token_count,
                            section_metadata={"sequence": chunk.sequence},
                            embedding=embedding,
                            parser_version=PARSER_VERSION,
                        )
                    )
                result = ExtractedResult(
                    document_id=document.id,
                    processing_run_id=run.id,
                    schema_version=extraction.schema_version,
                    model_output=extraction.model_dump(mode="json"),
                    approved_output=None,
                )
                session.add(result)
                await session.flush()
                for key, field in extraction.fields.items():
                    session.add(
                        ExtractionField(
                            result_id=result.id,
                            field_key=key,
                            value={"value": field.value},
                            confidence=Decimal(str(field.confidence)),
                            citations=[
                                citation.model_dump(mode="json") for citation in field.citations
                            ],
                        )
                    )
                for issue in issues:
                    session.add(
                        ValidationIssue(
                            document_id=document.id,
                            code=issue.code,
                            severity=issue.severity,
                            description=issue.description,
                            related_fields=list(issue.related_fields),
                            source_page=issue.source_page,
                            suggested_action=issue.suggested_action,
                        )
                    )
                    session.add(
                        AuditEvent(
                            event_type="validation_issue_created",
                            actor_id=None,
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            request_id=task.correlation_id,
                            safe_metadata={"code": issue.code, "severity": issue.severity},
                        )
                    )
                for signal in signals:
                    session.add(
                        SecurityEvent(
                            event_type="document_prompt_injection_signal",
                            severity="warning",
                            actor_id=None,
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            request_id=task.correlation_id,
                            safe_metadata=signal,
                        )
                    )
                require_legal_transition(DocumentStatus(document.status), DocumentStatus.EXTRACTING)
                require_legal_transition(DocumentStatus.EXTRACTING, DocumentStatus.INDEXING)
                target = DocumentStatus.NEEDS_REVIEW if issues or signals else DocumentStatus.READY
                require_legal_transition(DocumentStatus.INDEXING, target)
                document.status = target.value
                document.document_type = extraction.document_type.value
                document.detected_language = document_language(pages)
                run.status = "completed"
                run.parser_version = PARSER_VERSION
                run.model_version = self.provider.model_name
                run.prompt_version = PROMPT_VERSION
                run.finished_at = datetime.now(UTC)
                run.duration_ms = int((monotonic() - started) * 1000)
                session.add_all(
                    [
                        AuditEvent(
                            event_type="extraction_generated",
                            actor_id=None,
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            request_id=task.correlation_id,
                            safe_metadata={"schema_version": extraction.schema_version},
                        ),
                        AuditEvent(
                            event_type=f"document_{target.value}",
                            actor_id=None,
                            workspace_id=document.workspace_id,
                            document_id=document.id,
                            request_id=task.correlation_id,
                            safe_metadata={"issue_count": len(issues)},
                        ),
                    ]
                )
            return ProcessingOutcome("processed", False)
        except Exception as exc:
            await self._persist_failure(sessions, task, type(exc).__name__, started)
            raise
        finally:
            if temporary_path is not None:
                await anyio.Path(temporary_path).unlink(missing_ok=True)
                await anyio.Path(temporary_path.parent).rmdir()
            await engine.dispose()

    async def _document_path(self, document: Document) -> tuple[Path, Path | None]:
        if not document.storage_key:
            raise ValueError("Document has no stored object")
        if self.settings.storage_provider == "local":
            path = await LocalFileStorage(Path(self.settings.local_storage_root)).get(
                document.storage_key
            )
            return path, None
        if self.settings.storage_provider != "gcs" or not self.settings.gcs_bucket:
            raise RuntimeError("Worker storage provider is not configured")
        temporary = await anyio.to_thread.run_sync(
            lambda: tempfile.mkdtemp(prefix="gulfdocs-worker-")
        )
        path = Path(temporary) / "document.pdf"
        client = storage.Client(project=self.settings.gcp_project_id or None)
        await anyio.to_thread.run_sync(
            client.bucket(self.settings.gcs_bucket).blob(document.storage_key).download_to_filename,
            str(path),
        )
        return path, path

    async def _persist_failure(
        self,
        sessions: async_sessionmaker[AsyncSession],
        task: ProcessingTask,
        category: str,
        started: float,
    ) -> None:
        async with sessions.begin() as session:
            run = await session.get(
                DocumentProcessingRun, task.processing_run_id, with_for_update=True
            )
            document = await session.get(Document, task.document_id, with_for_update=True)
            if run is None or document is None or run.status == "completed":
                return
            if document.status != DocumentStatus.FAILED.value:
                require_legal_transition(DocumentStatus(document.status), DocumentStatus.FAILED)
                document.status = DocumentStatus.FAILED.value
            run.status = "failed"
            run.failure_category = category[:80]
            run.finished_at = datetime.now(UTC)
            run.duration_ms = int((monotonic() - started) * 1000)
            session.add(
                AuditEvent(
                    event_type="processing_failed",
                    actor_id=None,
                    workspace_id=document.workspace_id,
                    document_id=document.id,
                    request_id=task.correlation_id,
                    safe_metadata={"failure_category": category[:80]},
                )
            )
