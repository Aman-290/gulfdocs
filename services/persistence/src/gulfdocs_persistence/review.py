from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from gulfdocs_document_intelligence.models import DocumentStatus
from gulfdocs_document_intelligence.repositories import AuthIdentity
from gulfdocs_document_intelligence.status_machine import require_legal_transition
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AuditEvent,
    Document,
    DocumentReview,
    ExtractedResult,
    ExtractionField,
    ExtractionRevision,
    ValidationIssue,
)


class SqlAlchemyReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def extraction_for_workspace(
        self, workspace_id: UUID, document_id: UUID
    ) -> tuple[Document, ExtractedResult, list[ExtractionField], list[ValidationIssue]] | None:
        row = (
            await self.session.execute(
                select(Document, ExtractedResult)
                .join(ExtractedResult, ExtractedResult.document_id == Document.id)
                .where(
                    Document.workspace_id == workspace_id,
                    Document.id == document_id,
                    Document.status != DocumentStatus.DELETED.value,
                )
                .order_by(ExtractedResult.created_at.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        document, result = row
        fields = list(
            await self.session.scalars(
                select(ExtractionField)
                .where(ExtractionField.result_id == result.id)
                .order_by(ExtractionField.field_key)
            )
        )
        issues = list(
            await self.session.scalars(
                select(ValidationIssue)
                .where(ValidationIssue.document_id == document_id)
                .order_by(ValidationIssue.created_at)
            )
        )
        return document, result, fields, issues

    async def correct_field(
        self,
        *,
        identity: AuthIdentity,
        document_id: UUID,
        field_key: str,
        value: str | list[str] | None,
        reason: str | None,
        request_id: str,
    ) -> ExtractionField | None:
        row = await self.extraction_for_workspace(identity.workspace_id, document_id)
        if row is None:
            return None
        document, result, fields, _ = row
        field = next((item for item in fields if item.field_key == field_key), None)
        if field is None:
            field = ExtractionField(
                result_id=result.id,
                field_key=field_key,
                value={"value": None},
                confidence=0,
                citations=[],
            )
            self.session.add(field)
            await self.session.flush()
        previous = dict(field.value)
        revised: dict[str, Any] = {"value": value}
        self.session.add(
            ExtractionRevision(
                field_id=field.id,
                actor_id=identity.user_id,
                previous_value=previous,
                revised_value=revised,
                reason=reason,
            )
        )
        field.value = revised
        field.confidence = Decimal("1.0000")
        for issue in await self.session.scalars(
            select(ValidationIssue).where(
                ValidationIssue.document_id == document_id,
                ValidationIssue.resolved_at.is_(None),
            )
        ):
            if field_key in issue.related_fields:
                issue.resolved_at = datetime.now(UTC)
        self.session.add(
            AuditEvent(
                event_type="extraction_corrected",
                actor_id=identity.user_id,
                workspace_id=identity.workspace_id,
                document_id=document.id,
                request_id=request_id,
                safe_metadata={"field_key": field_key, "reason_supplied": bool(reason)},
            )
        )
        await self.session.flush()
        return field

    async def approve(
        self,
        *,
        identity: AuthIdentity,
        document_id: UUID,
        notes: str | None,
        request_id: str,
    ) -> Document | None:
        row = await self.extraction_for_workspace(identity.workspace_id, document_id)
        if row is None:
            return None
        document, result, fields, _ = row
        unresolved = await self.session.scalar(
            select(ValidationIssue.id).where(
                and_(
                    ValidationIssue.document_id == document_id,
                    ValidationIssue.resolved_at.is_(None),
                    ValidationIssue.severity.in_(("error", "critical")),
                )
            )
        )
        if unresolved is not None:
            raise ValueError("Document has unresolved blocking validation issues")
        current = DocumentStatus(document.status)
        require_legal_transition(current, DocumentStatus.APPROVED)
        document.status = DocumentStatus.APPROVED.value
        document.updated_at = datetime.now(UTC)
        result.approved_output = {field.field_key: field.value.get("value") for field in fields}
        self.session.add_all(
            [
                DocumentReview(
                    document_id=document.id,
                    reviewer_id=identity.user_id,
                    decision="approved",
                    notes=notes,
                ),
                AuditEvent(
                    event_type="document_approved",
                    actor_id=identity.user_id,
                    workspace_id=identity.workspace_id,
                    document_id=document.id,
                    request_id=request_id,
                    safe_metadata={"notes_supplied": bool(notes)},
                ),
            ]
        )
        await self.session.flush()
        return document
