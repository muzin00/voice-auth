from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from vca_auth.models import Speaker, Voiceprint


@dataclass
class AuthRegisterResult:
    """認証登録結果."""

    speaker: Speaker
    voiceprint: Voiceprint


@dataclass
class AuthVerifyResult:
    """認証結果（1:1照合）."""

    authenticated: bool
    speaker_id: str
    voice_similarity: float
    message: str


# =============================================================================
# WebSocket メッセージ型定義
# =============================================================================


class MessageType(str, Enum):
    """WebSocketメッセージタイプ."""

    PROMPTS = "prompts"
    ASR_RESULT = "asr_result"
    REGISTER_PIN = "register_pin"
    ENROLLMENT_COMPLETE = "enrollment_complete"
    ERROR = "error"


@dataclass
class EnrollmentPrompts:
    """Server → Client: プロンプト送信."""

    type: Literal["prompts"] = field(default="prompts", init=False)
    speaker_id: str = ""
    prompts: list[str] = field(default_factory=list)
    total_sets: int = 5
    current_set: int = 0

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "speaker_id": self.speaker_id,
            "prompts": self.prompts,
            "total_sets": self.total_sets,
            "current_set": self.current_set,
        }


@dataclass
class ASRResult:
    """Server → Client: ASR結果."""

    type: Literal["asr_result"] = field(default="asr_result", init=False)
    success: bool = False
    asr_result: str = ""
    set_index: int = 0
    remaining_sets: int = 0
    retry_count: int = 0
    max_retries: int = 5
    message: str = ""

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        result = {
            "type": self.type,
            "success": self.success,
            "asr_result": self.asr_result,
            "set_index": self.set_index,
            "message": self.message,
        }
        if self.success:
            result["remaining_sets"] = self.remaining_sets
        else:
            result["retry_count"] = self.retry_count
            result["max_retries"] = self.max_retries
        return result


@dataclass
class RegisterPinRequest:
    """Client → Server: PIN登録リクエスト."""

    type: Literal["register_pin"] = field(default="register_pin", init=False)
    pin: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "RegisterPinRequest":
        """辞書から生成."""
        return cls(pin=data.get("pin", ""))


@dataclass
class EnrollmentComplete:
    """Server → Client: 登録完了."""

    type: Literal["enrollment_complete"] = field(
        default="enrollment_complete", init=False
    )
    speaker_id: str = ""
    registered_digits: list[str] = field(default_factory=list)
    has_pin: bool = False
    status: str = "registered"

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "speaker_id": self.speaker_id,
            "registered_digits": self.registered_digits,
            "has_pin": self.has_pin,
            "status": self.status,
        }


@dataclass
class ErrorMessage:
    """Server → Client: エラーメッセージ."""

    type: Literal["error"] = field(default="error", init=False)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "code": self.code,
            "message": self.message,
        }


# =============================================================================
# 認証 (Verify) メッセージ
# =============================================================================


@dataclass
class VerifyChallenge:
    """Server → Client: 認証チャレンジ."""

    type: Literal["challenge"] = field(default="challenge", init=False)
    speaker_id: str = ""
    challenge: str = ""
    max_retries: int = 3

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "speaker_id": self.speaker_id,
            "challenge": self.challenge,
            "max_retries": self.max_retries,
        }


@dataclass
class VerifyResult:
    """Server → Client: 認証結果."""

    type: Literal["verify_result"] = field(default="verify_result", init=False)
    success: bool = False
    speaker_id: str = ""
    similarity: float = 0.0
    asr_result: str = ""
    retry_count: int = 0
    max_retries: int = 3
    message: str = ""

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "success": self.success,
            "speaker_id": self.speaker_id,
            "similarity": self.similarity,
            "asr_result": self.asr_result,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "message": self.message,
        }


# =============================================================================
# 識別 (Identify) メッセージ
# =============================================================================


@dataclass
class IdentifyChallenge:
    """Server → Client: 識別チャレンジ."""

    type: Literal["challenge"] = field(default="challenge", init=False)
    challenge: str = ""
    max_retries: int = 3

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "challenge": self.challenge,
            "max_retries": self.max_retries,
        }


@dataclass
class IdentifyCandidate:
    """識別候補."""

    speaker_id: str = ""
    similarity: float = 0.0

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "speaker_id": self.speaker_id,
            "similarity": self.similarity,
        }


@dataclass
class IdentifyResult:
    """Server → Client: 識別結果."""

    type: Literal["identify_result"] = field(default="identify_result", init=False)
    success: bool = False
    asr_result: str = ""
    candidates: list[IdentifyCandidate] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    message: str = ""

    def to_dict(self) -> dict:
        """辞書形式に変換."""
        return {
            "type": self.type,
            "success": self.success,
            "asr_result": self.asr_result,
            "candidates": [c.to_dict() for c in self.candidates],
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "message": self.message,
        }
