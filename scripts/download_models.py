#!/usr/bin/env python3
"""Download required models for VoiceAuth Server from Hugging Face.

Models:
- SenseVoice ASR (model.int8.onnx ~240MB)
- Silero VAD (~2MB)
- CAM++ Speaker Embedding (~30MB)
"""

import argparse
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download
from huggingface_hub.utils import HfHubHTTPError

MODELS = [
    {
        "repo_id": "csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "files": ["model.int8.onnx", "tokens.txt"],
        "subdir": "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "description": "SenseVoice ASR",
    },
    {
        "repo_id": "csukuangfj/vad",
        "files": ["silero_vad.onnx"],
        "subdir": None,
        "description": "Silero VAD",
    },
    {
        "repo_id": "csukuangfj/speaker-embedding-models",
        "files": ["3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"],
        "subdir": None,
        "description": "CAM++ Speaker Embedding",
    },
]


def download_model(
    repo_id: str,
    filename: str,
    local_dir: Path,
    subdir: str | None = None,
) -> Path:
    """Download a single model file from Hugging Face Hub.

    Args:
        repo_id: Hugging Face repository ID
        filename: Name of the file to download
        local_dir: Local directory to save the file
        subdir: Optional subdirectory within local_dir

    Returns:
        Path to the downloaded file
    """
    target_dir = local_dir / subdir if subdir else local_dir
    target_path = target_dir / filename

    if target_path.exists():
        print(f"  [SKIP] {filename} already exists")
        return target_path

    print(f"  [DOWNLOAD] {filename}...")
    downloaded_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )
    print(f"  [OK] {filename}")
    return Path(downloaded_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download VoiceAuth models from Hugging Face"
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("./models"),
        help="Directory to save models (default: ./models)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if files exist",
    )
    args = parser.parse_args()

    models_dir: Path = args.models_dir.resolve()
    models_dir.mkdir(parents=True, exist_ok=True)

    print("=== VoiceAuth Model Downloader ===")
    print(f"Target directory: {models_dir}")
    print()

    failed = []
    for model in MODELS:
        print(f"[{model['description']}]")
        for filename in model["files"]:
            try:
                download_model(
                    repo_id=model["repo_id"],
                    filename=filename,
                    local_dir=models_dir,
                    subdir=model["subdir"],
                )
            except HfHubHTTPError as e:
                print(f"  [ERROR] Failed to download {filename}: {e}")
                failed.append(f"{model['description']}/{filename}")
            except Exception as e:
                print(f"  [ERROR] Unexpected error downloading {filename}: {e}")
                failed.append(f"{model['description']}/{filename}")
        print()

    print("=== Download Complete ===")
    if failed:
        print(f"Failed downloads: {', '.join(failed)}")
        return 1

    # Show summary
    print("\nModel files:")
    for f in models_dir.rglob("*.onnx"):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.relative_to(models_dir)}: {size_mb:.1f} MB")

    total_size = sum(f.stat().st_size for f in models_dir.rglob("*") if f.is_file())
    print(f"\nTotal size: {total_size / (1024 * 1024):.1f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
