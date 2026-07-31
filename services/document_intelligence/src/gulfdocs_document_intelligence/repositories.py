from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from .models import DocumentStatus


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    user_id: UUID
    workspace_id: UUID
    auth_subject: str
    role: str
    email: str | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    id: UUID
    workspace_id: UUID
    created_by_id: UUID
    filename: str
    status: DocumentStatus
    size_bytes: int | None
    page_count: int | None
    content_type: str | None
    storage_key: str | None
    created_at: datetime
    updated_at: datetime
    document_type: str | None = None
    detected_language: str | None = None


class IdentityRepository(Protocol):
    async def get_or_create_identity(
        self,
        auth_subject: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> AuthIdentity: ...


class DocumentRepository(Protocol):
    async def get_for_workspace(
        self, workspace_id: UUID, document_id: UUID
    ) -> DocumentRecord | None: ...

    async def list_for_workspace(
        self, workspace_id: UUID, limit: int, offset: int
    ) -> list[DocumentRecord]: ...
