from fastapi.testclient import TestClient
from gulfdocs_api.main import app
from gulfdocs_document_intelligence.demo_data import DEMO_DOCUMENT_ID


def test_health_and_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"x-request-id": "test-request-001"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gulfdocs-api", "version": "0.1.0"}
    assert response.headers["x-request-id"] == "test-request-001"


def test_public_demo_is_synthetic_and_precomputed() -> None:
    with TestClient(app) as client:
        listing = client.get("/api/v1/demo/documents")
        answer = client.post(
            f"/api/v1/demo/documents/{DEMO_DOCUMENT_ID}/questions",
            json={"question": "What are the payment terms?"},
        )
    assert listing.status_code == 200
    assert listing.json()[0]["synthetic"] is True
    assert answer.status_code == 200
    assert answer.json()["model_name"] == "precomputed-public-demo"
    assert answer.json()["citations"][0]["page"] == 2


def test_unknown_question_returns_explicit_unsupported_answer() -> None:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/demo/documents/{DEMO_DOCUMENT_ID}/questions",
            json={"question": "Who won the football match?"},
        )
    assert response.status_code == 200
    assert response.json()["supported"] is False
    assert response.json()["citations"] == []
    assert "could not find enough evidence" in response.json()["answer"]


def test_anonymous_upload_endpoint_does_not_exist_in_phase_one() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/uploads/presign", json={"filename": "anything.pdf"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_validation_errors_do_not_expose_stack_traces() -> None:
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/demo/documents/{DEMO_DOCUMENT_ID}/questions", json={"question": "x"}
        )
    body = response.json()
    assert response.status_code == 422
    assert body["detail"] == "The request did not match the expected schema."
    assert "traceback" not in str(body).casefold()
