FROM ghcr.io/astral-sh/uv:0.9.18-python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/worker/pyproject.toml apps/worker/pyproject.toml
COPY services/document_intelligence/pyproject.toml services/document_intelligence/pyproject.toml
COPY services/persistence/pyproject.toml services/persistence/pyproject.toml
COPY apps/api/src apps/api/src
COPY services/document_intelligence/src services/document_intelligence/src
COPY services/persistence/src services/persistence/src
RUN uv sync --frozen --package gulfdocs-api --no-editable

USER 65532:65532
EXPOSE 8080
CMD ["/workspace/.venv/bin/uvicorn", "gulfdocs_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
