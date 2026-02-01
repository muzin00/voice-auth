"""登録フローの状態管理.

声紋登録WebSocketセッションの状態を管理する。
"""

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from numpy.typing import NDArray


class EnrollmentStatus(str, Enum):
    """登録フローのステータス."""

    WAITING_AUDIO = "waiting_audio"  # 音声待ち
    PROCESSING = "processing"  # 処理中
    WAITING_PIN = "waiting_pin"  # PIN入力待ち
    COMPLETED = "completed"  # 完了
    FAILED = "failed"  # 失敗


@dataclass
class EnrollmentState:
    """登録フローの状態.

    Attributes:
        speaker_id: 話者ID
        prompts: 生成されたプロンプト（4桁×5セット）
        current_set: 現在のセット番号（0〜4）
        retry_count: 現在のセットのリトライ回数
        max_retries: 最大リトライ回数
        status: 現在のステータス
        voiceprint_vectors: 数字別の声紋ベクトル（キー: "0"〜"9"）
        pin: 登録されたPIN
    """

    speaker_id: str
    prompts: list[str] = field(default_factory=list)
    current_set: int = 0
    retry_count: int = 0
    max_retries: int = 5
    status: EnrollmentStatus = EnrollmentStatus.WAITING_AUDIO
    voiceprint_vectors: dict[str, list[NDArray[np.float32]]] = field(
        default_factory=dict
    )
    pin: str | None = None

    @property
    def total_sets(self) -> int:
        """総セット数."""
        return len(self.prompts)

    @property
    def remaining_sets(self) -> int:
        """残りセット数."""
        return self.total_sets - self.current_set - 1

    @property
    def current_prompt(self) -> str | None:
        """現在のプロンプト."""
        if 0 <= self.current_set < len(self.prompts):
            return self.prompts[self.current_set]
        return None

    @property
    def is_all_sets_completed(self) -> bool:
        """すべてのセットが完了したか."""
        return self.current_set >= self.total_sets

    @property
    def registered_digits(self) -> list[str]:
        """登録済みの数字リスト."""
        return sorted(self.voiceprint_vectors.keys())

    def advance_to_next_set(self) -> None:
        """次のセットへ進む."""
        self.current_set += 1
        self.retry_count = 0
        if self.is_all_sets_completed:
            self.status = EnrollmentStatus.WAITING_PIN

    def increment_retry(self) -> bool:
        """リトライ回数をインクリメント.

        Returns:
            bool: リトライ可能な場合True、最大回数に達した場合False
        """
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            self.status = EnrollmentStatus.FAILED
            return False
        return True

    def add_voiceprint(self, digit: str, vector: NDArray[np.float32]) -> None:
        """声紋ベクトルを追加.

        同じ数字に対して複数のベクトルを保持する（後で平均化）。

        Args:
            digit: 数字（"0"〜"9"）
            vector: 声紋ベクトル
        """
        if digit not in self.voiceprint_vectors:
            self.voiceprint_vectors[digit] = []
        self.voiceprint_vectors[digit].append(vector)

    def set_pin(self, pin: str) -> None:
        """PINを設定.

        Args:
            pin: 4桁のPIN
        """
        self.pin = pin
        self.status = EnrollmentStatus.COMPLETED
