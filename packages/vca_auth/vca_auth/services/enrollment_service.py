"""声紋登録サービス.

声紋登録フローのビジネスロジックを提供する。
"""

import logging

import numpy as np
from numpy.typing import NDArray

from vca_auth.models import Speaker
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository
from vca_auth.services.enrollment_state import EnrollmentState

logger = logging.getLogger(__name__)


class EnrollmentService:
    """声紋登録サービス."""

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        voiceprint_repository: VoiceprintRepository,
    ):
        self.speaker_repository = speaker_repository
        self.voiceprint_repository = voiceprint_repository

    def save_enrollment(
        self,
        state: EnrollmentState,
    ) -> Speaker:
        """登録状態からスピーカーと声紋を保存.

        Args:
            state: 登録状態

        Returns:
            作成されたSpeaker
        """
        # スピーカーを作成または取得
        speaker = self.speaker_repository.get_by_speaker_id(state.speaker_id)
        if speaker is None:
            speaker = self.speaker_repository.create(
                Speaker(
                    speaker_id=state.speaker_id,
                    speaker_name=state.speaker_id,
                    pin_hash=self._hash_pin(state.pin) if state.pin else None,
                )
            )
            logger.info(f"Created new speaker: {state.speaker_id}")
        else:
            # 既存のスピーカーがいる場合はPINを更新
            if state.pin:
                speaker.pin_hash = self._hash_pin(state.pin)
                self.speaker_repository.update(speaker)
            # 既存の声紋を削除
            deleted = self.voiceprint_repository.delete_by_speaker_id(speaker.id)  # type: ignore
            logger.info(
                f"Deleted {deleted} existing voiceprints for {state.speaker_id}"
            )

        # 数字ごとの声紋を保存
        embeddings = self._average_embeddings(state.voiceprint_vectors)
        if embeddings:
            embeddings_bytes = {
                digit: embedding.tobytes() for digit, embedding in embeddings.items()
            }
            self.voiceprint_repository.create_bulk(
                speaker_id=speaker.id,  # type: ignore
                embeddings=embeddings_bytes,
            )
            logger.info(
                f"Saved {len(embeddings)} digit voiceprints for {state.speaker_id}"
            )

        return speaker

    def _average_embeddings(
        self,
        voiceprint_vectors: dict[str, list[NDArray[np.float32]]],
    ) -> dict[str, NDArray[np.float32]]:
        """各数字の声紋ベクトルを平均化.

        同じ数字に対して複数のベクトルがある場合、平均を取る。
        """
        result = {}
        for digit, vectors in voiceprint_vectors.items():
            if vectors:
                # 各ベクトルを正規化してから平均
                normalized = [v / np.linalg.norm(v) for v in vectors]
                avg = np.mean(normalized, axis=0)
                # 再度正規化
                result[digit] = avg / np.linalg.norm(avg)
        return result

    def _hash_pin(self, pin: str) -> str:
        """PINをハッシュ化.

        本番環境ではbcrypt等を使用すべき。
        """
        import hashlib

        return hashlib.sha256(pin.encode()).hexdigest()
