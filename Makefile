.PHONY: bootstrap install dev dev-web dev-api dev-worker db-up db-down migrate migration seed lint format typecheck test test-unit test-integration test-e2e eval build docker-build terraform-fmt terraform-validate smoke-local smoke-production

bootstrap: install db-up migrate seed

install:
	pnpm install --frozen-lockfile
	uv sync --all-packages

dev:
	@echo "Run 'make dev-web', 'make dev-api', and 'make dev-worker' in separate terminals."

dev-web:
	pnpm --filter @gulfdocs/web dev

dev-api:
	uv run uvicorn gulfdocs_api.main:app --app-dir apps/api/src --reload --port 8000

dev-worker:
	uv run uvicorn gulfdocs_worker.main:app --app-dir apps/worker/src --reload --port 8001

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	@echo "Alembic migrations are introduced in Phase 2."

migration:
	@echo "Alembic migrations are introduced in Phase 2."

seed:
	@echo "Database seed command is introduced in Phase 2; Phase 1 demo data is in-memory."

lint:
	pnpm lint
	uv run ruff check .

format:
	pnpm format
	uv run ruff format .

typecheck:
	pnpm typecheck
	uv run mypy apps/api/src apps/worker/src services/document_intelligence/src

test: test-unit

test-unit:
	pnpm test
	uv run pytest -m "not integration" --cov=apps/api/src --cov=apps/worker/src --cov=services/document_intelligence/src

test-integration:
	uv run pytest -m integration

test-e2e:
	pnpm --filter @gulfdocs/web test:e2e

eval:
	@echo "Evaluation commands are introduced in Phase 6."

build:
	pnpm build

docker-build:
	docker build -f apps/api/Dockerfile -t gulfdocs-api:local .
	docker build -f apps/worker/Dockerfile -t gulfdocs-worker:local .

terraform-fmt:
	terraform -chdir=infrastructure/terraform fmt -check -recursive

terraform-validate:
	terraform -chdir=infrastructure/terraform validate

smoke-local:
	uv run python tests/smoke_local.py

smoke-production:
	@test -n "$(API_BASE_URL)" || (echo "API_BASE_URL is required" && exit 1)
	uv run python tests/smoke_production.py
