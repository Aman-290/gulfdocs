import asyncio
import selectors
from collections.abc import Iterator
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from gulfdocs_api.config import get_settings
from gulfdocs_api.main import app
from gulfdocs_persistence.database import create_engine
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Synthetic GulfDocs integration test")
    content = document.tobytes()
    document.close()
    return content


async def _clear_database() -> None:
    engine = create_engine(get_settings().database_url)
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE organizations, users CASCADE"))
    await engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with asyncio.Runner(
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
    ) as runner:
        runner.run(_clear_database())
    settings = get_settings()
    original_root = settings.local_storage_root
    settings.local_storage_root = str(tmp_path / "storage")
    try:
        with TestClient(
            app,
            backend_options={
                "loop_factory": lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
            },
        ) as test_client:
            yield test_client
    finally:
        settings.local_storage_root = original_root


def _presign(client: TestClient, subject: str, content: bytes, key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/uploads/presign",
        headers={"Authorization": f"Bearer dev:{subject}", "Idempotency-Key": key},
        json={
            "filename": "invoice.pdf",
            "size_bytes": len(content),
            "content_type": "application/pdf",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_completion_and_workspace_isolation(client: TestClient) -> None:
    content = _pdf_bytes()
    presigned = _presign(client, "alice", content, "alice-upload-001")
    upload = client.put(
        str(presigned["upload_url"]),
        headers={"Content-Type": "application/pdf"},
        content=content,
    )
    assert upload.status_code == 204, upload.text

    complete = client.post(
        "/api/v1/uploads/complete",
        headers={"Authorization": "Bearer dev:alice"},
        json={"document_id": presigned["document_id"]},
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "queued"
    assert complete.json()["page_count"] == 1

    visible = client.get(
        f"/api/v1/documents/{presigned['document_id']}",
        headers={"Authorization": "Bearer dev:alice"},
    )
    hidden = client.get(
        f"/api/v1/documents/{presigned['document_id']}",
        headers={"Authorization": "Bearer dev:bob"},
    )
    assert visible.status_code == 200
    assert hidden.status_code == 404


def test_presign_is_idempotent(client: TestClient) -> None:
    content = _pdf_bytes()
    first = _presign(client, "alice", content, "alice-upload-002")
    second = _presign(client, "alice", content, "alice-upload-002")
    assert first["document_id"] == second["document_id"]
    assert first["upload_url"] == second["upload_url"]


def test_pdf_magic_is_checked_at_completion(client: TestClient) -> None:
    content = b"not really a pdf"
    presigned = _presign(client, "alice", content, "alice-upload-003")
    upload = client.put(
        str(presigned["upload_url"]),
        headers={"Content-Type": "application/pdf"},
        content=content,
    )
    assert upload.status_code == 204
    complete = client.post(
        "/api/v1/uploads/complete",
        headers={"Authorization": "Bearer dev:alice"},
        json={"document_id": presigned["document_id"]},
    )
    assert complete.status_code == 422
    assert complete.json()["detail"] == "File signature is not a PDF"
