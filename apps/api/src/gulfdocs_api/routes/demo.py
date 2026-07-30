from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from gulfdocs_document_intelligence.demo_data import (
    DEMO_DOCUMENT,
    DEMO_DOCUMENT_ID,
    answer_demo_question,
)
from gulfdocs_document_intelligence.models import (
    DemoDocumentDetail,
    DemoDocumentSummary,
    GroundedAnswer,
    QuestionRequest,
)

router = APIRouter(prefix="/api/v1/demo", tags=["public demo"])


@router.get(
    "/documents",
    response_model=list[DemoDocumentSummary],
    summary="List seeded synthetic demo documents",
)
async def list_demo_documents() -> list[DemoDocumentSummary]:
    return [DemoDocumentSummary.model_validate(DEMO_DOCUMENT.model_dump())]


@router.get(
    "/documents/{document_id}",
    response_model=DemoDocumentDetail,
    summary="Inspect one seeded synthetic demo document",
)
async def get_demo_document(document_id: UUID) -> DemoDocumentDetail:
    if document_id != DEMO_DOCUMENT_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo document not found")
    return DEMO_DOCUMENT


@router.post(
    "/documents/{document_id}/questions",
    response_model=GroundedAnswer,
    summary="Answer a bounded public-demo question from precomputed evidence",
)
async def ask_demo_document(document_id: UUID, payload: QuestionRequest) -> GroundedAnswer:
    if document_id != DEMO_DOCUMENT_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo document not found")
    return answer_demo_question(payload.question)
