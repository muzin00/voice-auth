"""声紋抽出サービス（sherpa-onnx CAM++）."""

from __future__ import annotations

import io
import logging
import struct
from typing import TYPE_CHECKING

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from vca_engine.converter import convert_to_wav

if TYPE_CHECKING:
    import sherpa_onnx

logger = logging.getLogger(__name__)


class VoiceprintService:
    """sherpa-onnx (CAM++) を使用した声紋抽出サービス."""

    # 出力ベクトルの次元数（3D-Speaker CAM++は512次元）
    EMBEDDING_DIM = 512

    def __init__(self, extractor: sherpa_onnx.SpeakerEmbeddingExtractor) -> None:
        """初期化.

        Args:
            extractor: sherpa_onnx.SpeakerEmbeddingExtractorインスタンス
        """
        self._extractor = extractor

    def extract(self, audio_bytes: bytes, audio_format: str = "wav") -> bytes:
        """音声データから声紋を抽出.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            声紋ベクトル（512次元のfloat32、2048バイト）
        """
        logger.info(
            f"Extracting voiceprint: {len(audio_bytes)} bytes, format={audio_format}"
        )

        try:
            # WAV形式に変換
            audio_bytes = convert_to_wav(audio_bytes, audio_format)
        except Exception as e:
            logger.error(f"Failed to convert audio to WAV: {e}")
            raise

        try:
            # soundfileで音声を読み込み
            samples, sample_rate = sf.read(
                io.BytesIO(audio_bytes), dtype="float32"
            )

            # ステレオの場合はモノラルに変換
            if len(samples.shape) > 1:
                samples = samples.mean(axis=1)

            # sherpa-onnxで声紋抽出
            stream = self._extractor.create_stream()
            stream.accept_waveform(sample_rate, samples)
            stream.input_finished()

            embedding = self._extractor.compute(stream)
            embedding_array = np.array(embedding, dtype=np.float32)

            logger.info(
                f"Voiceprint extracted successfully: shape={embedding_array.shape}, "
                f"dtype={embedding_array.dtype}"
            )

            return self._embedding_to_bytes(embedding_array)

        except Exception as e:
            logger.error(f"Voiceprint extraction failed: {e}")
            raise

    def _embedding_to_bytes(self, embedding: NDArray[np.float32]) -> bytes:
        """numpy配列をbytesに変換.

        Args:
            embedding: numpy配列（512次元）

        Returns:
            bytes（512 * 4 = 2048バイト）
        """
        # float32でパック
        return struct.pack(f"{self.EMBEDDING_DIM}f", *embedding.flatten())

    def _bytes_to_embedding(self, data: bytes) -> NDArray[np.float32]:
        """bytesをnumpy配列に変換.

        Args:
            data: bytes（512 * 4 = 2048バイト）

        Returns:
            numpy配列（512次元のfloat32）
        """
        values = struct.unpack(f"{self.EMBEDDING_DIM}f", data)
        return np.array(values, dtype=np.float32)

    def compare(self, embedding1: bytes, embedding2: bytes) -> float:
        """2つの声紋のコサイン類似度を計算.

        Args:
            embedding1: 声紋ベクトル1（bytes）
            embedding2: 声紋ベクトル2（bytes）

        Returns:
            コサイン類似度（0.0〜1.0）
        """
        vec1 = self._bytes_to_embedding(embedding1)
        vec2 = self._bytes_to_embedding(embedding2)

        # コサイン類似度
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = float(dot_product / (norm1 * norm2))
        logger.info(f"Voice similarity: {similarity:.4f}")
        return similarity
