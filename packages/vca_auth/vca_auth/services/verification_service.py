"""声紋認証サービス.

1:1照合（verify）と1:N識別（identify）のビジネスロジックを提供する。
"""

import logging
import random

import numpy as np
from numpy.typing import NDArray

from vca_auth.models import Speaker
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository

logger = logging.getLogger(__name__)


def generate_challenge() -> str:
    """認証用のチャレンジ（4桁の数字）を生成."""
    return "".join(random.choices("0123456789", k=4))


def cosine_similarity(
    a: NDArray[np.float32],
    b: NDArray[np.float32],
) -> float:
    """コサイン類似度を計算."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class VerificationService:
    """声紋認証サービス."""

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        voiceprint_repository: VoiceprintRepository,
        similarity_threshold: float = 0.6,
    ):
        self.speaker_repository = speaker_repository
        self.voiceprint_repository = voiceprint_repository
        self.similarity_threshold = similarity_threshold

    def verify(
        self,
        speaker_id: str,
        challenge: str,
        embeddings: dict[str, NDArray[np.float32]],
    ) -> tuple[bool, float, str]:
        """1:1照合を実行.

        Args:
            speaker_id: 話者ID
            challenge: チャレンジ文字列
            embeddings: 発話から抽出した数字別声紋

        Returns:
            (認証成功, 平均類似度, メッセージ)
        """
        speaker = self.speaker_repository.get_by_speaker_id(speaker_id)
        if speaker is None:
            return False, 0.0, "話者が見つかりません"

        if speaker.id is None:
            return False, 0.0, "話者IDが無効です"

        # チャレンジに含まれる各数字の声紋を照合
        similarities = []
        for digit in challenge:
            if digit not in embeddings:
                logger.warning(f"Missing embedding for digit {digit}")
                continue

            # 登録済みの声紋を取得
            stored = self.voiceprint_repository.get_by_speaker_id_and_digit(
                speaker.id, digit
            )
            if not stored:
                logger.warning(f"No stored voiceprint for digit {digit}")
                continue

            # 最新の声紋と比較
            stored_embedding = np.frombuffer(stored[0].embedding, dtype=np.float32)
            input_embedding = embeddings[digit]
            sim = cosine_similarity(stored_embedding, input_embedding)
            similarities.append(sim)
            logger.debug(f"Digit {digit}: similarity = {sim:.3f}")

        if not similarities:
            return False, 0.0, "照合可能な声紋がありません"

        avg_similarity = float(np.mean(similarities))
        is_verified = avg_similarity >= self.similarity_threshold

        if is_verified:
            message = "認証成功"
        else:
            message = f"類似度が閾値を下回りました ({avg_similarity:.2f} < {self.similarity_threshold})"

        return is_verified, avg_similarity, message

    def identify(
        self,
        challenge: str,
        embeddings: dict[str, NDArray[np.float32]],
        top_k: int = 3,
    ) -> list[tuple[Speaker, float]]:
        """1:N識別を実行.

        Args:
            challenge: チャレンジ文字列
            embeddings: 発話から抽出した数字別声紋
            top_k: 返す候補数

        Returns:
            [(Speaker, 平均類似度), ...] 類似度の高い順
        """
        speakers = self.speaker_repository.get_all()
        results = []

        for speaker in speakers:
            if speaker.id is None:
                continue

            # 各数字の声紋を照合
            similarities = []
            for digit in challenge:
                if digit not in embeddings:
                    continue

                stored = self.voiceprint_repository.get_by_speaker_id_and_digit(
                    speaker.id, digit
                )
                if not stored:
                    continue

                stored_embedding = np.frombuffer(stored[0].embedding, dtype=np.float32)
                input_embedding = embeddings[digit]
                sim = cosine_similarity(stored_embedding, input_embedding)
                similarities.append(sim)

            if similarities:
                avg_sim = float(np.mean(similarities))
                results.append((speaker, avg_sim))

        # 類似度でソート
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
