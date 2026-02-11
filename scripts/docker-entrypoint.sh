#!/bin/bash
set -e

# Download models if not present
if [ ! -f "/app/models/silero_vad.onnx" ]; then
    echo "=== Models not found. Downloading... ==="
    python /app/scripts/download_models.py --models-dir /app/models
    echo "=== Model download complete ==="
fi

exec "$@"
