"""声紋抽出サービス（WeSpeaker）."""

from __future__ import annotations

import logging
import struct
import tempfile
from typing import TYPE_CHECKING, cast

import numpy as np
from numpy.typing import NDArray

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

    def extract(self, audio_bytes: bytes) -> bytes:
        """音声データから声紋を抽出.

        Args:
            audio_bytes: 音声データ（WAV/MP3など）

        Returns:
            声紋ベクトル（256次元のfloat32、1024バイト）
        """
        # 一時ファイルに書き出してWeSpeakerで処理
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            logger.info(f"Extracting voiceprint from temp file: {tmp.name}")

            # WeSpeakerで声紋抽出
            embedding = cast(
                NDArray[np.float32], self._speaker.extract_embedding(tmp.name)
            )

            logger.info(
                f"Voiceprint extracted: shape={embedding.shape}, "
                f"dtype={embedding.dtype}"
            )

        # numpy配列をbytesに変換（float32）
        return self._embedding_to_bytes(embedding)

    def _embedding_to_bytes(self, embedding: NDArray[np.float32]) -> bytes:
        """numpy配列をbytesに変換.

        Args:
            embedding: numpy配列（256次元）

        Returns:
            bytes（256 * 4 = 1024バイト）
        """
        # float32でパック
        return struct.pack(f"{self.EMBEDDING_DIM}f", *embedding.flatten())
