.PHONY: test test-api test-auth test-engine test-infra lint format typecheck

# Run all tests (packages with tests)
test: test-auth test-engine test-infra

# Run tests for each package
test-api:
	uv run --package vca-api pytest packages/vca_api/tests/ -v

test-auth:
	uv run --package vca-auth pytest packages/vca_auth/tests/ -v

test-engine:
	uv run --package vca-engine pytest packages/vca_engine/tests/ -v

test-infra:
	uv run --package vca-infra pytest packages/vca_infra/tests/ -v

# Lint and format
lint:
	uv run ruff check .

format:
	uv run ruff check --fix . && uv run ruff format .

# Type check
typecheck:
	uv run pyright
