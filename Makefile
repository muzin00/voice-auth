.PHONY: test lint format typecheck run dev clean migrate

# Run all tests
test:
	uv run pytest voiceauth/ -v

# Run tests with coverage
test-cov:
	uv run pytest voiceauth/ -v --cov=voiceauth --cov-report=term-missing

# Lint
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff check --fix . && uv run ruff format .

# Type check
typecheck:
	uv run pyright

# Run server
run:
	uv run python main.py

# Run server with hot reload (development)
dev:
	uv run uvicorn voiceauth.app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(msg)"

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info

# Install dependencies
install:
	uv sync

# Install development dependencies
install-dev:
	uv sync --group dev
