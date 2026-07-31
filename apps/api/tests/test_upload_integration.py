import asyncio
import selectors
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import fitz
import psycopg
import pytest
from fastapi.testclient import TestClient
from gulfdocs_api.config import get_settings
from gulfdocs_api.main import app
from gulfdocs_persistence.database import create_engine
from gulfdocs_worker.config import WorkerSettings
from gulfdocs_worker.processor import PersistentDocumentProcessor, ProcessingTask
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Synthetic GulfDocs integration test")
    content = document.tobytes()
    document.close()
    return content


def _invoice_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "\n".join(
            (
                "Invoice number: INV-2026-100",
                "Supplier: Fictional Gulf Trading LLC",
                "Issue date: 2026-07-30",
                "Currency: AED",
                "Subtotal: 100.00",
                "VAT: 5.00",
                "Total: 105.00",
            )
        ),
    )
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


def _sync_database_url() -> str:
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")


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

    download = client.get(
        f"/api/v1/documents/{presigned['document_id']}/download",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert download.status_code == 200
    assert download.content == content

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

    hidden_delete = client.delete(
        f"/api/v1/documents/{presigned['document_id']}",
        headers={"Authorization": "Bearer dev:bob"},
    )
    deleted = client.delete(
        f"/api/v1/documents/{presigned['document_id']}",
        headers={"Authorization": "Bearer dev:alice"},
    )
    after_delete = client.get(
        f"/api/v1/documents/{presigned['document_id']}",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert hidden_delete.status_code == 404
    assert deleted.status_code == 204
    assert after_delete.status_code == 404


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


def test_only_failed_documents_can_be_retried(client: TestClient) -> None:
    content = _pdf_bytes()
    presigned = _presign(client, "alice", content, "alice-upload-004")
    client.put(
        str(presigned["upload_url"]),
        headers={"Content-Type": "application/pdf"},
        content=content,
    )
    client.post(
        "/api/v1/uploads/complete",
        headers={"Authorization": "Bearer dev:alice"},
        json={"document_id": presigned["document_id"]},
    )
    premature = client.post(
        f"/api/v1/documents/{presigned['document_id']}/retry",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert premature.status_code == 409

    with psycopg.connect(_sync_database_url()) as connection:
        connection.execute(
            "UPDATE documents SET status = 'failed' WHERE id = %s",
            (presigned["document_id"],),
        )
    retried = client.post(
        f"/api/v1/documents/{presigned['document_id']}/retry",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    with psycopg.connect(_sync_database_url()) as connection:
        attempts = connection.execute(
            "SELECT count(*) FROM document_processing_runs WHERE document_id = %s",
            (presigned["document_id"],),
        ).fetchone()
    assert attempts is not None and attempts[0] == 2


def test_daily_upload_limit_is_enforced(client: TestClient) -> None:
    settings = get_settings()
    original_limit = settings.max_uploads_per_user_per_day
    settings.max_uploads_per_user_per_day = 1
    try:
        content = _pdf_bytes()
        _presign(client, "alice", content, "alice-limit-001")
        blocked = client.post(
            "/api/v1/uploads/presign",
            headers={
                "Authorization": "Bearer dev:alice",
                "Idempotency-Key": "alice-limit-002",
            },
            json={
                "filename": "invoice.pdf",
                "size_bytes": len(content),
                "content_type": "application/pdf",
            },
        )
    finally:
        settings.max_uploads_per_user_per_day = original_limit
    assert blocked.status_code == 429


def test_persistent_worker_correction_approval_and_replay(client: TestClient) -> None:
    content = _invoice_pdf_bytes()
    presigned = _presign(client, "alice", content, "alice-process-001")
    assert (
        client.put(
            str(presigned["upload_url"]),
            headers={"Content-Type": "application/pdf"},
            content=content,
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/api/v1/uploads/complete",
            headers={"Authorization": "Bearer dev:alice"},
            json={"document_id": presigned["document_id"]},
        ).status_code
        == 200
    )
    with psycopg.connect(_sync_database_url()) as connection:
        run = connection.execute(
            "SELECT id, correlation_id, attempt "
            "FROM document_processing_runs WHERE document_id = %s",
            (presigned["document_id"],),
        ).fetchone()
    assert run is not None
    task = ProcessingTask(
        document_id=UUID(str(presigned["document_id"])),
        processing_run_id=run[0],
        correlation_id=run[1],
        attempt=run[2],
    )
    worker_settings = WorkerSettings(
        database_url=get_settings().database_url,
        storage_provider="local",
        local_storage_root=get_settings().local_storage_root,
        ai_provider="fake",
    )
    with asyncio.Runner(
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
    ) as runner:
        processed = runner.run(PersistentDocumentProcessor(worker_settings).process(task))
        replayed = runner.run(PersistentDocumentProcessor(worker_settings).process(task))
    assert processed.status == "processed"
    assert replayed.idempotent_replay is True

    extraction = client.get(
        f"/api/v1/documents/{presigned['document_id']}/extraction",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert extraction.status_code == 200, extraction.text
    assert extraction.json()["document_type"] == "invoice"
    correction = client.patch(
        f"/api/v1/documents/{presigned['document_id']}/extraction",
        headers={"Authorization": "Bearer dev:alice"},
        json={
            "field_key": "supplier_name",
            "value": "Corrected Fictional Supplier LLC",
            "reason": "Matched cited source",
        },
    )
    assert correction.status_code == 200
    approved = client.post(
        f"/api/v1/documents/{presigned['document_id']}/approve",
        headers={"Authorization": "Bearer dev:alice"},
        json={"notes": "Synthetic fixture reviewed"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    answer = client.post(
        f"/api/v1/documents/{presigned['document_id']}/questions",
        headers={"Authorization": "Bearer dev:alice"},
        json={"question": "What is the total?"},
    )
    assert answer.status_code == 201, answer.text
    assert answer.json()["supported"] is True
    assert answer.json()["citations"][0]["page"] == 1
    unauthorized_answer = client.post(
        f"/api/v1/documents/{presigned['document_id']}/questions",
        headers={"Authorization": "Bearer dev:bob"},
        json={"question": "What is the total?"},
    )
    assert unauthorized_answer.status_code == 404
    history = client.get(
        f"/api/v1/documents/{presigned['document_id']}/questions",
        headers={"Authorization": "Bearer dev:alice"},
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    unsupported = client.post(
        f"/api/v1/documents/{presigned['document_id']}/questions",
        headers={"Authorization": "Bearer dev:alice"},
        json={"question": "Who won the football championship?"},
    )
    assert unsupported.status_code == 201
    assert unsupported.json()["supported"] is False
    assert unsupported.json()["citations"] == []
    with psycopg.connect(_sync_database_url()) as connection:
        counts = connection.execute(
            "SELECT "
            "(SELECT count(*) FROM extraction_revisions), "
            "(SELECT count(*) FROM document_reviews), "
            "(SELECT count(*) FROM document_chunks WHERE document_id = %s)",
            (presigned["document_id"],),
        ).fetchone()
    assert counts is not None and counts[0] == 1 and counts[1] == 1 and counts[2] >= 1


def test_persistent_worker_records_non_retryable_storage_failure(client: TestClient) -> None:
    content = _pdf_bytes()
    presigned = _presign(client, "alice", content, "alice-process-failure")
    client.put(
        str(presigned["upload_url"]),
        headers={"Content-Type": "application/pdf"},
        content=content,
    )
    client.post(
        "/api/v1/uploads/complete",
        headers={"Authorization": "Bearer dev:alice"},
        json={"document_id": presigned["document_id"]},
    )
    with psycopg.connect(_sync_database_url()) as connection:
        row = connection.execute(
            "SELECT r.id, r.correlation_id, r.attempt, d.storage_key "
            "FROM document_processing_runs r JOIN documents d ON d.id = r.document_id "
            "WHERE d.id = %s",
            (presigned["document_id"],),
        ).fetchone()
    assert row is not None
    (Path(get_settings().local_storage_root) / row[3]).unlink()
    task = ProcessingTask(
        document_id=UUID(str(presigned["document_id"])),
        processing_run_id=row[0],
        correlation_id=row[1],
        attempt=row[2],
    )
    settings = WorkerSettings(
        database_url=get_settings().database_url,
        local_storage_root=get_settings().local_storage_root,
        storage_provider="local",
    )
    with (
        asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
        ) as runner,
        pytest.raises(FileNotFoundError),
    ):
        runner.run(PersistentDocumentProcessor(settings).process(task))
    with psycopg.connect(_sync_database_url()) as connection:
        status_row = connection.execute(
            "SELECT d.status, r.status, r.failure_category "
            "FROM documents d JOIN document_processing_runs r ON r.document_id = d.id "
            "WHERE d.id = %s",
            (presigned["document_id"],),
        ).fetchone()
    assert status_row is not None
    assert status_row[0:2] == ("failed", "failed")
    assert status_row[2] == "FileNotFoundError"
