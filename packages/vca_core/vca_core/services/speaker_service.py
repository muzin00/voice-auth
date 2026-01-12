from vca_core.interfaces.speaker_repository import SpeakerRepositoryProtocol
from vca_core.models.speaker import Speaker


class SpeakerService:
    def __init__(self, repository: SpeakerRepositoryProtocol):
        self.repository = repository

    def register_speaker(
        self,
        speaker_id: str,
        speaker_name: str | None = None,
    ) -> Speaker:
        existing = self.repository.get_by_speaker_id(speaker_id)
        if existing:
            return existing

        speaker = Speaker(speaker_id=speaker_id, speaker_name=speaker_name)
        return self.repository.create(speaker)
