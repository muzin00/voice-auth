# --- Stage 1: Builder (Production dependencies) ---
FROM python:3.11-slim AS builder
ENV UV_NO_CACHE=1
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Install dependencies only (skips project installation to cache layers)
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 2: Dev Builder (includes dev dependencies) ---
FROM builder AS dev-builder

# Install dev dependencies
RUN uv sync --frozen --no-install-project

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
ENV PYTHONDONTWRITEBYTECODE=1

# Copy uv binary and virtual environment from dev-builder
COPY --from=dev-builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=dev-builder /app/.venv /app/.venv

# Copy dependency files for uv sync
COPY pyproject.toml uv.lock ./

# Note: Source code is mounted via docker-compose volume
CMD ["python", "main.py"]

# --- Stage 6: Production ---
FROM runtime-base AS prod
ENV PORT=8000

# Copy uv binary and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY pyproject.toml uv.lock ./
COPY voiceauth/ ./voiceauth/
COPY main.py ./

# Install the project itself into the environment
RUN uv sync --frozen --no-dev

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

CMD ["python", "main.py"]
