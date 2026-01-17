from sqlmodel import Session, func, select
from vca_core.models import Passphrase


class PassphraseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        speaker_id: int,
        voice_sample_id: int,
        phrase: str,
    ) -> Passphrase:
        passphrase = Passphrase(
            speaker_id=speaker_id,
            voice_sample_id=voice_sample_id,
            phrase=phrase,
        )
        self.session.add(passphrase)
        self.session.commit()
        self.session.refresh(passphrase)
        return passphrase

    def get_by_speaker_id(self, speaker_id: int) -> list[Passphrase]:
        statement = select(Passphrase).where(Passphrase.speaker_id == speaker_id)
        return list(self.session.exec(statement).all())

    def get_by_public_id(self, public_id: str) -> Passphrase | None:
        statement = select(Passphrase).where(Passphrase.public_id == public_id)
        return self.session.exec(statement).first()

    def count_by_speaker_id(self, speaker_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Passphrase)
            .where(Passphrase.speaker_id == speaker_id)
        )
        result = self.session.exec(statement).one()
        return int(result)
