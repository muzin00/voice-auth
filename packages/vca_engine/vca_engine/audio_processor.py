"""音声処理パイプライン.

VAD → ASR → 声紋抽出のパイプライン処理を提供する。
"""

import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from vca_engine.loader import get_asr, get_speaker_extractor, get_vad
from vca_engine.settings import engine_settings

logger = logging.getLogger(__name__)


@dataclass
class AudioProcessResult:
    """音声処理結果."""

    asr_text: str
    embedding: NDArray[np.float32] | None
    has_speech: bool
    duration_seconds: float


def bytes_to_samples(audio_bytes: bytes) -> NDArray[np.float32]:
    """バイト列を音声サンプルに変換.

    16bit PCM (little-endian) を float32 に変換。

    Args:
        audio_bytes: 16bit PCM音声データ

    Returns:
        float32の音声サンプル配列 (-1.0 〜 1.0)
    """
    # 16bit PCMをint16として読み込み
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    # float32に変換 (-1.0 〜 1.0)
    return samples.astype(np.float32) / 32768.0


def samples_to_bytes(samples: NDArray[np.float32]) -> bytes:
    """音声サンプルをバイト列に変換.

    float32 を 16bit PCM (little-endian) に変換。

    Args:
        samples: float32の音声サンプル配列 (-1.0 〜 1.0)

    Returns:
        16bit PCM音声データ
    """
    # float32をint16に変換
    int_samples = (samples * 32767).astype(np.int16)
    return int_samples.tobytes()


def detect_speech_segments(
    samples: NDArray[np.float32],
) -> list[tuple[int, int]]:
    """VADで音声区間を検出.

    Args:
        samples: 音声サンプル配列

    Returns:
        音声区間のリスト [(start_sample, end_sample), ...]
    """
    try:
        vad = get_vad()
    except RuntimeError:
        # VADがロードされていない場合は全体を音声とみなす
        logger.warning("VAD not loaded, treating entire audio as speech")
        return [(0, len(samples))]

    # VADをリセット
    vad.reset()

    # サンプルを処理
    vad.accept_waveform(samples)

    # 音声区間を取得
    segments = []
    while not vad.empty():
        segment = vad.front()
        segments.append((segment.start, segment.start + len(segment.samples)))
        vad.pop()

    return segments


def recognize_speech(samples: NDArray[np.float32]) -> str:
    """ASRで音声認識.

    Args:
        samples: 音声サンプル配列

    Returns:
        認識テキスト
    """
    try:
        asr = get_asr()
    except RuntimeError:
        logger.warning("ASR not loaded, returning empty string")
        return ""

    stream = asr.create_stream()
    stream.accept_waveform(engine_settings.SAMPLE_RATE, samples)
    asr.decode(stream)

    return stream.result.text.strip()


def extract_embedding(samples: NDArray[np.float32]) -> NDArray[np.float32] | None:
    """声紋埋め込みを抽出.

    Args:
        samples: 音声サンプル配列

    Returns:
        声紋ベクトル (192次元) or None
    """
    try:
        extractor = get_speaker_extractor()
    except RuntimeError:
        logger.warning("Speaker extractor not loaded")
        return None

    stream = extractor.create_stream()
    stream.accept_waveform(engine_settings.SAMPLE_RATE, samples)
    stream.input_finished()

    if not extractor.is_ready(stream):
        logger.warning("Not enough audio for speaker embedding")
        return None

    embedding = extractor.compute(stream)
    return np.array(embedding, dtype=np.float32)


def process_audio(audio_bytes: bytes) -> AudioProcessResult:
    """音声データを処理.

    VAD → ASR → 声紋抽出のパイプライン処理。

    Args:
        audio_bytes: 16bit PCM音声データ

    Returns:
        AudioProcessResult: 処理結果
    """
    samples = bytes_to_samples(audio_bytes)
    duration = len(samples) / engine_settings.SAMPLE_RATE

    # VADで音声区間を検出
    segments = detect_speech_segments(samples)

    if not segments:
        return AudioProcessResult(
            asr_text="",
            embedding=None,
            has_speech=False,
            duration_seconds=duration,
        )

    # 音声区間を結合
    speech_samples = np.concatenate([samples[start:end] for start, end in segments])

    # ASRで認識
    asr_text = recognize_speech(speech_samples)

    # 声紋抽出
    embedding = extract_embedding(speech_samples)

    return AudioProcessResult(
        asr_text=asr_text,
        embedding=embedding,
        has_speech=True,
        duration_seconds=duration,
    )


def extract_digit_embeddings(
    audio_bytes: bytes,
    expected_digits: str,
) -> dict[str, NDArray[np.float32]]:
    """数字ごとの声紋を抽出.

    4桁の数字を発話した音声から、各数字の声紋を抽出する。
    VADで検出された音声区間を4分割して各数字に対応させる。

    Args:
        audio_bytes: 16bit PCM音声データ
        expected_digits: 期待される数字列 (例: "4326")

    Returns:
        数字と声紋のマッピング {"4": embedding, "3": embedding, ...}
    """
    samples = bytes_to_samples(audio_bytes)

    # VADで音声区間を検出
    segments = detect_speech_segments(samples)

    if not segments:
        return {}

    # 音声区間を結合
    speech_samples = np.concatenate([samples[start:end] for start, end in segments])

    # 4分割して各数字の声紋を抽出
    num_digits = len(expected_digits)
    if num_digits == 0:
        return {}

    segment_length = len(speech_samples) // num_digits
    if segment_length < 1600:  # 最低100msは必要
        logger.warning("Audio too short for digit segmentation")
        return {}

    result = {}
    for i, digit in enumerate(expected_digits):
        start = i * segment_length
        end = start + segment_length if i < num_digits - 1 else len(speech_samples)
        digit_samples = speech_samples[start:end]

        embedding = extract_embedding(digit_samples)
        if embedding is not None:
            result[digit] = embedding

    return result
