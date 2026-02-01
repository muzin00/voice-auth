# --- Stage 1: Metadata Planner ---
# Extracts pyproject.toml files to optimize build cache for monorepos
FROM python:3.11-slim AS planner
WORKDIR /app
COPY . .
RUN find packages -type f ! -name "pyproject.toml" -delete

# --- Stage 2: Builder (Production) ---
FROM python:3.11-slim AS builder
ENV UV_NO_CACHE=1
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml uv.lock ./
COPY --from=planner /app/packages/ packages/

# Install dependencies only (skips project root installation to cache layers)
RUN uv sync --frozen --no-dev --no-install-workspace

# --- Stage 3: Model Downloader ---
FROM python:3.11-slim AS model-downloader
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Copy and run download script
COPY scripts/download_models.sh ./scripts/
RUN chmod +x ./scripts/download_models.sh && ./scripts/download_models.sh ./models

# --- Stage 4: Runtime (Production) ---
FROM python:3.11-slim AS runner
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 libsndfile1 make && rm -rf /var/lib/apt/lists/*

# Copy uv binary and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . .

# Install the project itself into the environment
RUN uv sync --frozen --no-dev

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

CMD ["python", "main.py"]
