from sqlmodel import Session, select

from vca_auth.models.speaker import Speaker


class SpeakerRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, speaker: Speaker) -> Speaker:
        self.session.add(speaker)
        self.session.commit()
        self.session.refresh(speaker)
        return speaker

    def update(self, speaker: Speaker) -> Speaker:
        self.session.add(speaker)
        self.session.commit()
        self.session.refresh(speaker)
        return speaker

    def get_by_speaker_id(self, speaker_id: str) -> Speaker | None:
        statement = select(Speaker).where(Speaker.speaker_id == speaker_id)
        return self.session.exec(statement).first()

    def get_by_id(self, id: int) -> Speaker | None:
        statement = select(Speaker).where(Speaker.id == id)
        return self.session.exec(statement).first()

    def get_all(self) -> list[Speaker]:
        """すべての話者を取得."""
        statement = select(Speaker)
        return list(self.session.exec(statement).all())

    def delete(self, speaker: Speaker) -> None:
        self.session.delete(speaker)
        self.session.commit()
