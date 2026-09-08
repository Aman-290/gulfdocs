import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID

import anyio
from google.api_core.exceptions import AlreadyExists
from google.cloud import storage, tasks_v2  # type: ignore[attr-defined]
from google.cloud.tasks_v2.types import HttpMethod


class GcsSignedUploadAdapter:
    def __init__(self, bucket_name: str) -> None:
        if not bucket_name:
            raise RuntimeError("GCS_BUCKET is required for Cloud Storage uploads")
        self.bucket = storage.Client().bucket(bucket_name)

    async def create_upload_url(
        self, object_key: str, expires_at: datetime, content_type: str
    ) -> str:
        blob = self.bucket.blob(object_key)
        return await anyio.to_thread.run_sync(
            lambda: blob.generate_signed_url(
                version="v4",
                expiration=expires_at,
                method="PUT",
                content_type=content_type,
            )
        )

    async def download_to_temporary_path(self, object_key: str) -> Path:
        descriptor, name = mkstemp(suffix=".pdf")
        os.close(descriptor)
        path = Path(name)
        try:
            await anyio.to_thread.run_sync(
                self.bucket.blob(object_key).download_to_filename, str(path)
            )
        except Exception:
            await anyio.Path(path).unlink(missing_ok=True)
            raise
        return path

    async def create_download_url(self, object_key: str, expires_at: datetime) -> str:
        blob = self.bucket.blob(object_key)
        return await anyio.to_thread.run_sync(
            lambda: blob.generate_signed_url(version="v4", expiration=expires_at, method="GET")
        )

    async def delete(self, object_key: str) -> None:
        await anyio.to_thread.run_sync(self.bucket.blob(object_key).delete)


@dataclass(frozen=True, slots=True)
class QueueConfiguration:
    project_id: str
    region: str
    queue: str
    worker_url: str
    invoker_service_account: str
    oidc_audience: str = ""


class CloudTasksQueueAdapter:
    def __init__(self, configuration: QueueConfiguration) -> None:
        if not all(
            (
                configuration.project_id,
                configuration.region,
                configuration.queue,
                configuration.worker_url,
                configuration.invoker_service_account,
            )
        ):
            raise RuntimeError("Cloud Tasks configuration is incomplete")
        self.configuration = configuration
        self.client = tasks_v2.CloudTasksAsyncClient()

    async def enqueue_document(
        self,
        document_id: UUID,
        processing_run_id: UUID,
        correlation_id: str,
        attempt: int,
    ) -> str:
        parent = self.client.queue_path(
            self.configuration.project_id,
            self.configuration.region,
            self.configuration.queue,
        )
        payload = json.dumps(
            {
                "document_id": str(document_id),
                "processing_run_id": str(processing_run_id),
                "correlation_id": correlation_id,
                "attempt": attempt,
            }
        ).encode()
        task_name = f"{parent}/tasks/gulfdocs-{processing_run_id.hex}"
        task = {
            "name": task_name,
            "http_request": {
                "http_method": HttpMethod.POST,
                "url": self.configuration.worker_url,
                "headers": {"Content-Type": "application/json"},
                "body": payload,
                "oidc_token": {
                    "service_account_email": self.configuration.invoker_service_account,
                    "audience": self.configuration.oidc_audience or self.configuration.worker_url,
                },
            },
        }
        try:
            created = await self.client.create_task(request={"parent": parent, "task": task})
        except AlreadyExists:
            return task_name
        return created.name


class DevelopmentTaskQueueAdapter:
    async def enqueue_document(
        self,
        document_id: UUID,
        processing_run_id: UUID,
        correlation_id: str,
        attempt: int,
    ) -> str:
        del document_id, correlation_id, attempt
        return f"development-{processing_run_id}"
