import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from gulfdocs_api.config import get_settings
from gulfdocs_api.main import app
from gulfdocs_api.rate_limit import FixedWindowLimiter
from gulfdocs_document_intelligence.demo_data import DEMO_DOCUMENT_ID


def test_health_and_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"x-request-id": "test-request-001"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gulfdocs-api", "version": "0.1.0"}
    assert response.headers["x-request-id"] == "test-request-001"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


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


def test_anonymous_upload_endpoint_is_protected() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/uploads/presign", json={"filename": "anything.pdf"})
    assert response.status_code == 401
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


async def test_public_demo_limiter_returns_retryable_429() -> None:
    settings = get_settings()
    original_limit = settings.public_demo_requests_per_minute
    settings.public_demo_requests_per_minute = 1
    limiter = FixedWindowLimiter()
    request = Request({"type": "http", "client": ("203.0.113.9", 443)})
    try:
        await limiter(request)
        with pytest.raises(HTTPException) as raised:
            await limiter(request)
    finally:
        settings.public_demo_requests_per_minute = original_limit
    assert raised.value.status_code == 429
    assert raised.value.headers == {"Retry-After": "60"}
