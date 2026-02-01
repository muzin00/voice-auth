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

# --- Stage 2b: Builder (Development/Test) ---
FROM python:3.11-slim AS builder-dev
ENV UV_NO_CACHE=1
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml uv.lock ./
COPY --from=planner /app/packages/ packages/

# Install dependencies including dev dependencies
RUN uv sync --frozen --no-install-workspace

# --- Stage 3: Model Downloader ---
FROM python:3.11-slim AS model-downloader
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl bzip2 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p models && \
    # Silero VAD model
    curl -L -o models/silero_vad.onnx \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx && \
    # CAM++ Speaker Embedding model
    curl -L -o models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx && \
    # SenseVoice ASR model
    curl -L -o /tmp/sensevoice.tar.bz2 \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2 && \
    tar -xjf /tmp/sensevoice.tar.bz2 -C models && \
    rm /tmp/sensevoice.tar.bz2

# --- Stage 4: Runtime (Production) ---
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

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

CMD ["python", "main.py"]

# --- Stage 5: Test Runner ---
FROM python:3.11-slim AS test
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 libsndfile1 && rm -rf /var/lib/apt/lists/*

# Copy uv binary and virtual environment from dev builder
COPY --from=builder-dev /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder-dev /app/.venv /app/.venv

# Copy application source code
COPY . .

# Install the project itself into the environment (with dev dependencies)
RUN uv sync --frozen

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

# Default command runs all tests
CMD ["uv", "run", "pytest", "-v"]
