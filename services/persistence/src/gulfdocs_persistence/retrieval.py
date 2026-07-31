from datetime import UTC, datetime
from uuid import UUID

from gulfdocs_document_intelligence.repositories import AuthIdentity
from gulfdocs_document_intelligence.retrieval import RetrievalCandidate
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DailyUsageLimit, Document, DocumentChunk, DocumentQuestion


class SqlAlchemyRetrievalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def full_text_search(
        self, *, workspace_id: UUID, document_id: UUID, query: str, limit: int = 12
    ) -> list[RetrievalCandidate]:
        tsquery = func.websearch_to_tsquery("simple", query)
        score = func.ts_rank_cd(DocumentChunk.search_vector, tsquery)
        rows = (
            await self.session.execute(
                select(DocumentChunk, score.label("score"))
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.workspace_id == workspace_id,
                    DocumentChunk.document_id == document_id,
                    Document.workspace_id == workspace_id,
                    DocumentChunk.search_vector.op("@@")(tsquery),
                )
                .order_by(score.desc(), DocumentChunk.id)
                .limit(limit)
            )
        ).all()
        return [
            RetrievalCandidate(
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                text=chunk.chunk_text,
                language=chunk.detected_language,
                rank=index,
                source="fts",
                score=float(value),
            )
            for index, (chunk, value) in enumerate(rows, start=1)
        ]

    async def semantic_search(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        embedding: list[float],
        limit: int = 12,
        maximum_distance: float = 0.65,
    ) -> list[RetrievalCandidate]:
        distance = DocumentChunk.embedding.cosine_distance(embedding)
        rows = (
            await self.session.execute(
                select(DocumentChunk, distance.label("distance"))
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.workspace_id == workspace_id,
                    DocumentChunk.document_id == document_id,
                    Document.workspace_id == workspace_id,
                    DocumentChunk.embedding.is_not(None),
                    distance <= maximum_distance,
                )
                .order_by(distance, DocumentChunk.id)
                .limit(limit)
            )
        ).all()
        return [
            RetrievalCandidate(
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                text=chunk.chunk_text,
                language=chunk.detected_language,
                rank=index,
                source="semantic",
                score=1 - float(value),
            )
            for index, (chunk, value) in enumerate(rows, start=1)
        ]

    async def consume_question_allowance(
        self,
        identity: AuthIdentity,
        document_id: UUID,
        *,
        maximum_daily: int,
        maximum_document: int,
    ) -> bool:
        document = await self.session.scalar(
            select(Document.id).where(
                Document.id == document_id,
                Document.workspace_id == identity.workspace_id,
                Document.status.in_(("ready", "needs_review", "approved")),
            )
        )
        if document is None:
            return False
        document_count = await self.session.scalar(
            select(func.count(DocumentQuestion.id)).where(
                DocumentQuestion.document_id == document_id,
                DocumentQuestion.actor_id == identity.user_id,
            )
        )
        if (document_count or 0) >= maximum_document:
            return False
        today = datetime.now(UTC).date()
        usage = await self.session.scalar(
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
        if usage is None:
            usage = DailyUsageLimit(
                workspace_id=identity.workspace_id,
                user_id=identity.user_id,
                usage_date=today,
            )
            self.session.add(usage)
            await self.session.flush()
        if usage.question_count >= maximum_daily:
            return False
        usage.question_count += 1
        await self.session.flush()
        return True
