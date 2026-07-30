from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from gulfdocs_document_intelligence.models import DocumentStatus
from gulfdocs_document_intelligence.repositories import AuthIdentity, DocumentRecord
from gulfdocs_document_intelligence.status_machine import require_legal_transition
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AuditEvent,
    DailyUsageLimit,
    Document,
    DocumentProcessingRun,
    DocumentUpload,
    Membership,
    Organization,
    User,
)


def _document_record(document: Document) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        workspace_id=document.workspace_id,
        created_by_id=document.created_by_id,
        filename=document.safe_display_name,
        status=DocumentStatus(document.status),
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        content_type=document.content_type,
        storage_key=document.storage_key,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


class SqlAlchemyIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_identity(
        self,
        auth_subject: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> AuthIdentity:
        statement = (
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(User.auth_subject == auth_subject, User.disabled.is_(False))
            .order_by(Membership.created_at)
            .limit(1)
        )
        row = (await self.session.execute(statement)).first()
        if row is None:
            user_id = uuid5(NAMESPACE_URL, f"gulfdocs:user:{auth_subject}")
            workspace_id = uuid5(NAMESPACE_URL, f"gulfdocs:workspace:{auth_subject}")
            safe_suffix = str(user_id).split("-")[0]
            user = User(
                id=user_id,
                auth_subject=auth_subject,
                email=email,
                display_name=display_name,
            )
            organization = Organization(
                id=workspace_id,
                name=f"{display_name or 'Personal'} workspace",
                slug=f"personal-{safe_suffix}",
                is_personal=True,
            )
            self.session.add_all([user, organization])
            await self.session.flush()
            membership = Membership(
                organization_id=workspace_id,
                user_id=user_id,
                role="owner",
            )
            self.session.add(membership)
            await self.session.flush()
        else:
            user, membership = row
            user_id = user.id
            workspace_id = membership.organization_id
            email = user.email
            display_name = user.display_name
        return AuthIdentity(
            user_id=user_id,
            workspace_id=workspace_id,
            auth_subject=auth_subject,
            role="owner" if row is None else membership.role,
            email=email,
            display_name=display_name,
        )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_workspace(
        self, workspace_id: UUID, document_id: UUID
    ) -> DocumentRecord | None:
        document = await self._get_model(workspace_id, document_id)
        return _document_record(document) if document else None

    async def list_for_workspace(
        self, workspace_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[DocumentRecord]:
        statement = (
            select(Document)
            .where(Document.workspace_id == workspace_id, Document.status != "deleted")
            .order_by(Document.updated_at.desc())
            .limit(min(limit, 100))
            .offset(max(offset, 0))
        )
        documents = (await self.session.scalars(statement)).all()
        return [_document_record(document) for document in documents]

    async def find_upload_by_idempotency(
        self, workspace_id: UUID, idempotency_key: str
    ) -> tuple[Document, DocumentUpload] | None:
        statement = (
            select(Document, DocumentUpload)
            .join(DocumentUpload, DocumentUpload.document_id == Document.id)
            .where(
                DocumentUpload.workspace_id == workspace_id,
                DocumentUpload.idempotency_key == idempotency_key,
            )
        )
        row = (await self.session.execute(statement)).first()
        return (row[0], row[1]) if row is not None else None

    async def create_pending_upload(
        self,
        *,
        identity: AuthIdentity,
        filename: str,
        expected_size_bytes: int,
        idempotency_key: str,
        token_hash: str,
        object_key: str,
        expires_at: datetime,
        request_id: str,
        document_id: UUID,
    ) -> tuple[Document, DocumentUpload]:
        existing = await self.find_upload_by_idempotency(identity.workspace_id, idempotency_key)
        if existing is not None:
            return existing
        document = Document(
            id=document_id,
            workspace_id=identity.workspace_id,
            created_by_id=identity.user_id,
            original_filename=filename,
            safe_display_name=filename,
            status=DocumentStatus.PENDING_UPLOAD.value,
        )
        self.session.add(document)
        await self.session.flush()
        upload = DocumentUpload(
            workspace_id=identity.workspace_id,
            document_id=document.id,
            idempotency_key=idempotency_key,
            upload_token_hash=token_hash,
            object_key=object_key,
            expected_size_bytes=expected_size_bytes,
            expires_at=expires_at,
            status="pending",
        )
        self.session.add_all(
            [
                upload,
                AuditEvent(
                    event_type="document_created",
                    actor_id=identity.user_id,
                    workspace_id=identity.workspace_id,
                    document_id=document.id,
                    request_id=request_id,
                    safe_metadata={"filename_length": len(filename)},
                ),
            ]
        )
        await self.session.flush()
        return document, upload

    async def get_upload_for_workspace(
        self, workspace_id: UUID, document_id: UUID, *, for_update: bool = False
    ) -> tuple[Document, DocumentUpload] | None:
        statement: Select[tuple[Document, DocumentUpload]] = (
            select(Document, DocumentUpload)
            .join(DocumentUpload, DocumentUpload.document_id == Document.id)
            .where(Document.workspace_id == workspace_id, Document.id == document_id)
        )
        if for_update:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).first()
        return (row[0], row[1]) if row is not None else None

    async def get_upload_by_document(
        self, document_id: UUID, *, for_update: bool = False
    ) -> tuple[Document, DocumentUpload] | None:
        statement: Select[tuple[Document, DocumentUpload]] = (
            select(Document, DocumentUpload)
            .join(DocumentUpload, DocumentUpload.document_id == Document.id)
            .where(Document.id == document_id)
        )
        if for_update:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).first()
        return (row[0], row[1]) if row is not None else None

    async def complete_upload(
        self,
        *,
        identity: AuthIdentity,
        document_id: UUID,
        storage_key: str,
        content_sha256: str,
        size_bytes: int,
        page_count: int,
        request_id: str,
    ) -> DocumentRecord | None:
        row = await self.get_upload_for_workspace(
            identity.workspace_id, document_id, for_update=True
        )
        if row is None:
            return None
        document, upload = row
        if upload.status == "uploaded":
            return _document_record(document)
        require_legal_transition(DocumentStatus(document.status), DocumentStatus.UPLOADED)
        upload.status = "uploaded"
        upload.completed_at = datetime.now(UTC)
        document.status = DocumentStatus.UPLOADED.value
        document.storage_key = storage_key
        document.content_sha256 = content_sha256
        document.content_type = "application/pdf"
        document.size_bytes = size_bytes
        document.page_count = page_count
        document.updated_at = datetime.now(UTC)
        self.session.add(
            AuditEvent(
                event_type="upload_completed",
                actor_id=identity.user_id,
                workspace_id=identity.workspace_id,
                document_id=document.id,
                request_id=request_id,
                safe_metadata={"size_bytes": size_bytes, "page_count": page_count},
            )
        )
        await self.session.flush()
        return _document_record(document)

    async def transition(
        self,
        *,
        identity: AuthIdentity,
        document_id: UUID,
        target: DocumentStatus,
        request_id: str,
    ) -> DocumentRecord | None:
        document = await self._get_model(identity.workspace_id, document_id, for_update=True)
        if document is None:
            return None
        current = DocumentStatus(document.status)
        require_legal_transition(current, target)
        document.status = target.value
        document.updated_at = datetime.now(UTC)
        self.session.add(
            AuditEvent(
                event_type=f"document_{target.value}",
                actor_id=identity.user_id,
                workspace_id=identity.workspace_id,
                document_id=document.id,
                request_id=request_id,
                safe_metadata={"previous_status": current.value},
            )
        )
        await self.session.flush()
        return _document_record(document)

    async def create_processing_run(
        self, *, document_id: UUID, correlation_id: str
    ) -> DocumentProcessingRun:
        latest_attempt = await self.session.scalar(
            select(func.max(DocumentProcessingRun.attempt)).where(
                DocumentProcessingRun.document_id == document_id
            )
        )
        processing_run = DocumentProcessingRun(
            document_id=document_id,
            task_id=None,
            correlation_id=correlation_id,
            status="dispatching",
            attempt=(latest_attempt or 0) + 1,
        )
        self.session.add(processing_run)
        await self.session.flush()
        return processing_run

    async def attach_processing_task(self, processing_run_id: UUID, task_id: str) -> None:
        processing_run = await self.session.get(DocumentProcessingRun, processing_run_id)
        if processing_run is None:
            raise LookupError("Processing run was not found")
        processing_run.task_id = task_id
        processing_run.status = "queued"
        await self.session.flush()

    async def consume_upload_allowance(self, identity: AuthIdentity, maximum: int) -> bool:
        today = datetime.now(UTC).date()
        statement = (
            select(DailyUsageLimit)
            .where(
                and_(
                    DailyUsageLimit.workspace_id == identity.workspace_id,
                    DailyUsageLimit.user_id == identity.user_id,
                    DailyUsageLimit.usage_date == today,
                )
            )
            .with_for_update()
        )
        usage = await self.session.scalar(statement)
        if usage is None:
            usage = DailyUsageLimit(
                workspace_id=identity.workspace_id,
                user_id=identity.user_id,
                usage_date=today,
            )
            self.session.add(usage)
            await self.session.flush()
        if usage.upload_count >= maximum:
            return False
        usage.upload_count += 1
        await self.session.flush()
        return True

    async def _get_model(
        self, workspace_id: UUID, document_id: UUID, *, for_update: bool = False
    ) -> Document | None:
        statement = select(Document).where(
            Document.workspace_id == workspace_id,
            Document.id == document_id,
            Document.status != "deleted",
        )
        if for_update:
            statement = statement.with_for_update()
        document: Document | None = await self.session.scalar(statement)
        return document
