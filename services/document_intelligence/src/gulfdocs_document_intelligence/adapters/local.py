import shutil
from pathlib import Path
from uuid import UUID, uuid4

from .ports import TaskHandler


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def put(self, workspace_id: UUID, document_id: UUID, source: Path) -> str:
        object_key = f"{workspace_id}/{document_id}/{uuid4()}.pdf"
        await self.put_at(object_key, source)
        return object_key

    async def put_at(self, object_key: str, source: Path) -> None:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Unsafe storage object path")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    async def get(self, object_key: str) -> Path:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents or not target.is_file():
            raise FileNotFoundError("Stored object was not found")
        return target

    async def delete(self, object_key: str) -> None:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Unsafe storage object path")
        target.unlink(missing_ok=True)


class InlineTaskQueue:
    def __init__(self, handler: TaskHandler) -> None:
        self.handler = handler

    async def enqueue_document(
        self,
        document_id: UUID,
        processing_run_id: UUID,
        correlation_id: str,
        attempt: int,
    ) -> str:
        del processing_run_id, attempt
        task_id = f"inline-{uuid4()}"
        await self.handler(document_id, correlation_id)
        return task_id
