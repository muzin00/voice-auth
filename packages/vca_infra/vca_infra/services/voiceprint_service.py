"""声紋抽出サービス（WeSpeaker）."""

from __future__ import annotations

import logging
import struct
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from numpy.typing import NDArray

from vca_infra.utils.audio_converter import convert_to_wav

if TYPE_CHECKING:
    from wespeakerruntime import Speaker

logger = logging.getLogger(__name__)


class VoiceprintService:
    """WeSpeakerを使用した声紋抽出サービス."""

    # 出力ベクトルの次元数
    EMBEDDING_DIM = 256

    def __init__(self, speaker_model: Speaker) -> None:
        """初期化.

        Args:
            speaker_model: wespeakerruntime.Speakerインスタンス
        """
        self._speaker = speaker_model

    def extract(self, audio_bytes: bytes, audio_format: str = "wav") -> bytes:
        """音声データから声紋を抽出.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            声紋ベクトル（256次元のfloat32、1024バイト）
        """
        logger.info(
            f"Extracting voiceprint: {len(audio_bytes)} bytes, format={audio_format}"
        )

        try:
            # 内部でサンプリングレートなどの正規化も行うとより安全
            audio_bytes = convert_to_wav(audio_bytes, audio_format)
        except Exception as e:
            logger.error(f"Failed to convert audio to WAV: {e}")
            raise

        tmp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.wav"

        try:
            tmp_path.write_bytes(audio_bytes)

            # 抽出処理
            raw_embedding = self._speaker.extract_embedding(str(tmp_path))
            embedding = cast(NDArray[np.float32], raw_embedding)

            logger.info(
                f"Voiceprint extracted successfully: shape={embedding.shape}, "
                f"dtype={embedding.dtype}"
            )

            # 正常に抽出できた場合のみbytesに変換して返す
            return self._embedding_to_bytes(embedding)

        except Exception as e:
            logger.error(f"Voiceprint extraction failed: {e}")
            raise
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def _embedding_to_bytes(self, embedding: NDArray[np.float32]) -> bytes:
        """numpy配列をbytesに変換.

        Args:
            embedding: numpy配列（256次元）

        Returns:
            bytes（256 * 4 = 1024バイト）
        """
        # float32でパック
        return struct.pack(f"{self.EMBEDDING_DIM}f", *embedding.flatten())

    def _bytes_to_embedding(self, data: bytes) -> NDArray[np.float32]:
        """bytesをnumpy配列に変換.

        Args:
            data: bytes（256 * 4 = 1024バイト）

        Returns:
            numpy配列（256次元のfloat32）
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
