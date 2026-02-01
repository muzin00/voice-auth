from dataclasses import dataclass

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
