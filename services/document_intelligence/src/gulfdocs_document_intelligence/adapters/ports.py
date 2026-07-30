from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol
from uuid import UUID


class StoragePort(Protocol):
    async def put(self, workspace_id: UUID, document_id: UUID, source: Path) -> str: ...

    async def get(self, object_key: str) -> Path: ...

    async def delete(self, object_key: str) -> None: ...


TaskHandler = Callable[[UUID, str], Awaitable[None]]


class TaskQueuePort(Protocol):
    async def enqueue_document(self, document_id: UUID, correlation_id: str) -> str: ...
