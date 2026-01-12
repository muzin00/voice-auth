from typing import Protocol

from vca_core.models.speaker import Speaker


class SpeakerRepositoryProtocol(Protocol):
    def create(self, speaker: Speaker) -> Speaker: ...

    def get_by_speaker_id(self, speaker_id: str) -> Speaker | None: ...
