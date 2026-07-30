from .models import DocumentStatus


class IllegalStatusTransition(ValueError):
    """Raised when code attempts an invalid document state transition."""


LEGAL_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.PENDING_UPLOAD: frozenset({DocumentStatus.UPLOADED, DocumentStatus.DELETED}),
    DocumentStatus.UPLOADED: frozenset(
        {DocumentStatus.QUEUED, DocumentStatus.FAILED, DocumentStatus.DELETED}
    ),
    DocumentStatus.QUEUED: frozenset(
        {DocumentStatus.VALIDATING, DocumentStatus.FAILED, DocumentStatus.DELETED}
    ),
    DocumentStatus.VALIDATING: frozenset({DocumentStatus.EXTRACTING, DocumentStatus.FAILED}),
    DocumentStatus.EXTRACTING: frozenset({DocumentStatus.INDEXING, DocumentStatus.FAILED}),
    DocumentStatus.INDEXING: frozenset(
        {DocumentStatus.READY, DocumentStatus.NEEDS_REVIEW, DocumentStatus.FAILED}
    ),
    DocumentStatus.READY: frozenset(
        {DocumentStatus.NEEDS_REVIEW, DocumentStatus.APPROVED, DocumentStatus.DELETED}
    ),
    DocumentStatus.NEEDS_REVIEW: frozenset(
        {DocumentStatus.READY, DocumentStatus.APPROVED, DocumentStatus.DELETED}
    ),
    DocumentStatus.APPROVED: frozenset({DocumentStatus.DELETED}),
    DocumentStatus.FAILED: frozenset({DocumentStatus.QUEUED, DocumentStatus.DELETED}),
    DocumentStatus.DELETED: frozenset(),
}


def require_legal_transition(current: DocumentStatus, target: DocumentStatus) -> None:
    if target not in LEGAL_TRANSITIONS[current]:
        raise IllegalStatusTransition(f"Cannot transition document from {current} to {target}")
