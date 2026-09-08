from uuid import uuid4

from fastapi.testclient import TestClient
from gulfdocs_worker.config import get_worker_settings
from gulfdocs_worker.main import app


def test_worker_rejects_public_unauthenticated_invocation() -> None:
    payload = {
        "document_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "correlation_id": "test-task-1",
    }
    with TestClient(app) as client:
        response = client.post("/internal/tasks/process-document", json=payload)
    assert response.status_code == 401


def test_retention_endpoint_rejects_public_unauthenticated_invocation() -> None:
    with TestClient(app) as client:
        response = client.post("/internal/retention/cleanup")
    assert response.status_code == 401


def test_development_task_delivery_is_identifier_only_and_idempotent() -> None:
    payload = {
        "document_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "correlation_id": "test-task-2",
    }
    headers = {"authorization": "Bearer local-development-only"}
    with TestClient(app) as client:
        first = client.post("/internal/tasks/process-document", json=payload, headers=headers)
        second = client.post("/internal/tasks/process-document", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.json()["status"] == "already_processed"
    assert second.json()["idempotent_replay"] is True
    assert "pdf" not in payload and "secret" not in payload


def test_oidc_mode_fails_closed_when_configuration_is_missing() -> None:
    settings = get_worker_settings()
    original_mode = settings.worker_auth_mode
    settings.worker_auth_mode = "oidc"
    try:
        with TestClient(app) as client:
            response = client.post(
                "/internal/tasks/process-document",
                headers={"authorization": "Bearer unverified"},
                json={
                    "document_id": str(uuid4()),
                    "processing_run_id": str(uuid4()),
                    "correlation_id": "test-task-oidc",
                },
            )
    finally:
        settings.worker_auth_mode = original_mode
    assert response.status_code == 503
