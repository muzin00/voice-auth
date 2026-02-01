#!/bin/bash
# Download required models for VCA Server from Hugging Face
#
# Models:
# - SenseVoice ASR (model.int8.onnx ~240MB)
# - Silero VAD (~2MB)
# - CAM++ Speaker Embedding (~30MB)

set -e

MODELS_DIR="${1:-./models}"
mkdir -p "$MODELS_DIR"

# Hugging Face base URL
HF_BASE="https://huggingface.co"

echo "=== VCA Server Model Downloader ==="
echo "Source: Hugging Face"
echo "Target directory: $MODELS_DIR"
echo ""

# SenseVoice ASR Model
SENSEVOICE_DIR="$MODELS_DIR/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
SENSEVOICE_REPO="csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"

if [ -f "$SENSEVOICE_DIR/model.int8.onnx" ] && [ -f "$SENSEVOICE_DIR/tokens.txt" ]; then
    echo "[SenseVoice] Already exists, skipping..."
else
    echo "[SenseVoice] Downloading ASR model (~240MB)..."
    mkdir -p "$SENSEVOICE_DIR"

    # Download model.int8.onnx
    curl -L -o "$SENSEVOICE_DIR/model.int8.onnx" \
        "$HF_BASE/$SENSEVOICE_REPO/resolve/main/model.int8.onnx"

    # Download tokens.txt
    curl -L -o "$SENSEVOICE_DIR/tokens.txt" \
        "$HF_BASE/$SENSEVOICE_REPO/resolve/main/tokens.txt"

    echo "[SenseVoice] Done!"
fi

# Silero VAD Model
VAD_FILE="$MODELS_DIR/silero_vad.onnx"
VAD_REPO="csukuangfj/vad"

if [ -f "$VAD_FILE" ]; then
    echo "[Silero VAD] Already exists, skipping..."
else
    echo "[Silero VAD] Downloading VAD model (~2MB)..."
    curl -L -o "$VAD_FILE" \
        "$HF_BASE/$VAD_REPO/resolve/main/silero_vad.onnx"
    echo "[Silero VAD] Done!"
fi

# CAM++ Speaker Embedding Model
SPEAKER_FILE="$MODELS_DIR/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"
SPEAKER_REPO="csukuangfj/speaker-embedding-models"

if [ -f "$SPEAKER_FILE" ]; then
    echo "[CAM++] Already exists, skipping..."
else
    echo "[CAM++] Downloading speaker embedding model (~30MB)..."
    curl -L -o "$SPEAKER_FILE" \
        "$HF_BASE/$SPEAKER_REPO/resolve/main/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"
    echo "[CAM++] Done!"
fi

echo ""
echo "=== Download Complete ==="
echo ""
echo "Model files:"
ls -lh "$MODELS_DIR"/*.onnx 2>/dev/null || true
ls -lh "$SENSEVOICE_DIR"/*.onnx 2>/dev/null || true
ls -lh "$SENSEVOICE_DIR"/*.txt 2>/dev/null || true
echo ""
echo "Total size:"
du -sh "$MODELS_DIR"
