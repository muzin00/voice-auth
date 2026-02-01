from sqlmodel import Session, select
from vca_core.models import Voiceprint


class VoiceprintRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        speaker_id: int,
        embedding: bytes,
    ) -> Voiceprint:
        voiceprint = Voiceprint(
            speaker_id=speaker_id,
            embedding=embedding,
        )
        self.session.add(voiceprint)
        self.session.commit()
        self.session.refresh(voiceprint)
        return voiceprint

    def get_by_speaker_id(self, speaker_id: int) -> list[Voiceprint]:
        statement = select(Voiceprint).where(Voiceprint.speaker_id == speaker_id)
        return list(self.session.exec(statement).all())

    def get_by_public_id(self, public_id: str) -> Voiceprint | None:
        statement = select(Voiceprint).where(Voiceprint.public_id == public_id)
        return self.session.exec(statement).first()
