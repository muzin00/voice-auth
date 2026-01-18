FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TORCHAUDIO_BACKEND=soundfile

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Pre-download models to avoid loading delay at runtime
RUN python -c "import wespeakerruntime; wespeakerruntime.Speaker(lang='en')"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

CMD ["python", "main.py"]
