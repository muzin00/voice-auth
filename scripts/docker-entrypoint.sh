#!/bin/bash
set -e

# Download models if not present
MODELS_DIR="${ENGINE_MODELS_DIR:-/var/lib/voiceauth/models}"
if [ ! -f "${MODELS_DIR}/silero_vad.onnx" ]; then
    echo "=== Models not found. Downloading... ==="
    python /app/scripts/download_models.py --models-dir "${MODELS_DIR}"
    echo "=== Model download complete ==="
fi

exec "$@"
