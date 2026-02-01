# --- Stage 1: Metadata Planner ---
# Extracts pyproject.toml files to optimize build cache for monorepos
FROM python:3.11-slim AS planner
WORKDIR /app
COPY . .
RUN find packages -type f ! -name "pyproject.toml" -delete

# --- Stage 2: Builder ---
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

# --- Stage 3: Runtime ---
FROM python:3.11-slim AS runner
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 libsndfile1 && rm -rf /var/lib/apt/lists/*

# Copy uv binary and virtual environment from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . .

# Install the project itself into the environment
RUN uv sync --frozen --no-dev

# Pre-download models to avoid runtime download delays
RUN mkdir -p models && \
    curl -L -o models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx

CMD ["python", "main.py"]
