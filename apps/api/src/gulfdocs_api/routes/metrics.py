from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Any

from fastapi import APIRouter
from gulfdocs_persistence.models import (
    DailyUsageLimit,
    Document,
    DocumentProcessingRun,
    LLMUsageEvent,
)
from sqlalchemy import func, select

from ..config import get_settings
from ..dependencies import Authorized
from ..schemas import DailyTokenSummary, MetricsSummary, QualitySummary, UsageSummary

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummary)
async def metrics_summary(context: Authorized) -> MetricsSummary:
    settings = get_settings()
    today = datetime.now(UTC).date()
    usage = await context.session.scalar(
        select(DailyUsageLimit).where(
            DailyUsageLimit.workspace_id == context.identity.workspace_id,
            DailyUsageLimit.user_id == context.identity.user_id,
            DailyUsageLimit.usage_date == today,
        )
    )
    status_rows = (
        await context.session.execute(
            select(Document.status, func.count(Document.id))
            .where(
                Document.workspace_id == context.identity.workspace_id,
                Document.status != "deleted",
            )
            .group_by(Document.status)
        )
    ).all()
    status_counts = {str(status): int(count) for status, count in status_rows}
    total = sum(status_counts.values())
    durations = list(
        await context.session.scalars(
            select(DocumentProcessingRun.duration_ms)
            .join(Document, Document.id == DocumentProcessingRun.document_id)
            .where(
                Document.workspace_id == context.identity.workspace_id,
                DocumentProcessingRun.duration_ms.is_not(None),
            )
        )
    )
    duration_values = sorted(int(value) for value in durations if value is not None)
    daily_rows = (
        await context.session.execute(
            select(
                func.date(LLMUsageEvent.created_at),
                func.sum(LLMUsageEvent.input_tokens + LLMUsageEvent.output_tokens),
            )
            .where(
                LLMUsageEvent.workspace_id == context.identity.workspace_id,
                LLMUsageEvent.created_at >= datetime.now(UTC) - timedelta(days=7),
            )
            .group_by(func.date(LLMUsageEvent.created_at))
            .order_by(func.date(LLMUsageEvent.created_at))
        )
    ).all()
    return MetricsSummary(
        generated_at=datetime.now(UTC),
        usage=UsageSummary(
            usage_date=today,
            uploads_used=usage.upload_count if usage else 0,
            uploads_limit=settings.max_uploads_per_user_per_day,
            questions_used=usage.question_count if usage else 0,
            questions_limit=settings.max_questions_per_user_per_day,
            generated_tokens=usage.generated_tokens if usage else 0,
        ),
        quality=QualitySummary(
            total_documents=total,
            failed_documents=status_counts.get("failed", 0),
            needs_review_documents=status_counts.get("needs_review", 0),
            approved_documents=status_counts.get("approved", 0),
            failure_rate=_ratio(status_counts.get("failed", 0), total),
            needs_review_rate=_ratio(status_counts.get("needs_review", 0), total),
            average_processing_ms=_average(duration_values),
            median_processing_ms=float(median(duration_values)) if duration_values else None,
            p95_processing_ms=_percentile(duration_values, 0.95),
        ),
        daily_tokens=[
            DailyTokenSummary(date=_as_date(day), tokens=int(tokens or 0))
            for day, tokens in daily_rows
        ],
    )


def _ratio(value: int, total: int) -> float:
    return round(value / total, 4) if total else 0.0


def _average(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _percentile(values: list[int], percentile: float) -> float | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, int((len(values) - 1) * percentile + 0.9999)))
    return float(values[index])


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
