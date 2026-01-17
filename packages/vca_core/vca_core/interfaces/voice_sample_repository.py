from typing import Protocol

from vca_core.models import VoiceSample


class VoiceSampleRepositoryProtocol(Protocol):
    def create(
        self,
        speaker_id: int,
        audio_file_path: str,
        audio_format: str,
        sample_rate: int | None = None,
        channels: int | None = None,
    ) -> VoiceSample: ...

    def get_by_id(self, voice_sample_id: int) -> VoiceSample | None: ...

    def get_by_public_id(self, public_id: str) -> VoiceSample | None: ...
