from typing import Protocol

from vca_core.models import Passphrase


class PassphraseRepositoryProtocol(Protocol):
    def create(
        self,
        speaker_id: int,
        voice_sample_id: int,
        phrase: str,
    ) -> Passphrase: ...

    def get_by_speaker_id(self, speaker_id: int) -> list[Passphrase]: ...

    def get_by_public_id(self, public_id: str) -> Passphrase | None: ...

    def count_by_speaker_id(self, speaker_id: int) -> int: ...
