# --- Stage 1: Builder (Production dependencies) ---
FROM python:3.11-slim AS builder

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv optimization settings
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Install dependencies only (skips project installation to cache layers)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

# --- Stage 2: Dev Builder (includes dev dependencies) ---
FROM builder AS dev-builder

# Install dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# --- Stage 3: Model Downloader ---
FROM python:3.11-slim AS model-downloader
WORKDIR /app

# Install huggingface_hub for model download
COPY scripts/requirements.txt ./scripts/
RUN pip install --no-cache-dir -r scripts/requirements.txt

# Copy and run download script
COPY scripts/download_models.py ./scripts/
RUN python scripts/download_models.py --models-dir ./models

# --- Stage 4: Runtime Base ---
FROM python:3.11-slim AS runtime-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 libsndfile1 && rm -rf /var/lib/apt/lists/*

# --- Stage 5: Development ---
FROM runtime-base AS dev

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment from dev-builder
COPY --from=dev-builder /app/.venv /app/.venv

# Copy dependency files for uv sync
COPY pyproject.toml uv.lock ./

# Copy entrypoint script (auto-downloads models if missing)
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Note: Source code is mounted via docker-compose volume
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "main.py"]

# --- Stage 6: Production ---
FROM runtime-base AS prod
ENV PORT=8000

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY pyproject.toml uv.lock alembic.ini ./
COPY voiceauth/ ./voiceauth/
COPY main.py ./

# Install the project itself into the environment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

CMD ["python", "main.py"]
