from typing import Protocol

from vca_core.models import Voiceprint


class VoiceprintRepositoryProtocol(Protocol):
    def create(
        self,
        speaker_id: int,
        voice_sample_id: int,
        embedding: bytes,
    ) -> Voiceprint: ...

    def get_by_speaker_id(self, speaker_id: int) -> list[Voiceprint]: ...

    def get_by_public_id(self, public_id: str) -> Voiceprint | None: ...
