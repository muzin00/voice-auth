from typing import Protocol

from vca_auth.models.speaker import Speaker
from vca_auth.models.voiceprint import Voiceprint


class SpeakerRepositoryProtocol(Protocol):
    """話者リポジトリのプロトコル."""

    def create(self, speaker: Speaker) -> Speaker: ...

    def get_by_speaker_id(self, speaker_id: str) -> Speaker | None: ...


class VoiceprintRepositoryProtocol(Protocol):
    """声紋リポジトリのプロトコル."""

    def create(self, speaker_id: int, embedding: bytes) -> Voiceprint: ...

    def get_by_speaker_id(self, speaker_id: int) -> list[Voiceprint]: ...

    def get_by_public_id(self, public_id: str) -> Voiceprint | None: ...


class VoiceprintEngineProtocol(Protocol):
    """声紋エンジンのプロトコル（vca_engine が実装する）."""

    def extract(self, audio_bytes: bytes, audio_format: str = "wav") -> bytes:
        """声紋を抽出."""
        ...

    def compare(self, embedding1: bytes, embedding2: bytes) -> float:
        """2つの声紋を比較."""
        ...
