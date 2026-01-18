"""音声フォーマット変換ユーティリティ."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def convert_to_wav(audio_bytes: bytes, source_format: str) -> bytes:
    """任意の音声フォーマットをWAVに変換.

    Args:
        audio_bytes: 音声データ（任意のフォーマット）
        source_format: 元のフォーマット（webm, mp3, m4a等）

    Returns:
        WAV形式の音声データ（16bit PCM, モノラル）
    """
    logger.info(f"Converting {source_format} to WAV: {len(audio_bytes)} bytes")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-f",
                source_format,  # 入力フォーマット
                "-i",
                "pipe:0",  # 標準入力から読み込み
                "-ar",
                "16000",  # サンプルレート: 16kHz
                "-ac",
                "1",  # チャンネル数: モノラル
                "-sample_fmt",
                "s16",  # サンプルフォーマット: 16bit
                "-f",
                "wav",  # 出力フォーマット: WAV
                "pipe:1",  # 標準出力に書き込み
            ],
            input=audio_bytes,
            capture_output=True,
            check=True,
        )

        wav_bytes = result.stdout
        logger.info(f"Conversion complete: {len(wav_bytes)} bytes")
        return wav_bytes

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        logger.error(f"FFmpeg conversion failed: {error_msg}")
        raise RuntimeError(f"Audio conversion failed: {error_msg}") from e
