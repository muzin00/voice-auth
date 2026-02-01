from sqlmodel import Session, select

from vca_auth.models import Voiceprint


class VoiceprintRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        speaker_id: int,
        embedding: bytes,
        digit: str | None = None,
    ) -> Voiceprint:
        voiceprint = Voiceprint(
            speaker_id=speaker_id,
            embedding=embedding,
            digit=digit,
        )
        self.session.add(voiceprint)
        self.session.commit()
        self.session.refresh(voiceprint)
        return voiceprint

    def create_bulk(
        self,
        speaker_id: int,
        embeddings: dict[str, bytes],
    ) -> list[Voiceprint]:
        """複数の数字別声紋を一括作成."""
        voiceprints = []
        for digit, embedding in embeddings.items():
            voiceprint = Voiceprint(
                speaker_id=speaker_id,
                embedding=embedding,
                digit=digit,
            )
            self.session.add(voiceprint)
            voiceprints.append(voiceprint)

        self.session.commit()
        for vp in voiceprints:
            self.session.refresh(vp)
        return voiceprints

    def get_by_speaker_id(self, speaker_id: int) -> list[Voiceprint]:
        statement = select(Voiceprint).where(Voiceprint.speaker_id == speaker_id)
        return list(self.session.exec(statement).all())

    def get_by_speaker_id_and_digit(
        self,
        speaker_id: int,
        digit: str,
    ) -> list[Voiceprint]:
        """特定の話者と数字の声紋を取得."""
        statement = select(Voiceprint).where(
            Voiceprint.speaker_id == speaker_id,
            Voiceprint.digit == digit,
        )
        return list(self.session.exec(statement).all())

    def get_digits_by_speaker_id(self, speaker_id: int) -> list[str]:
        """話者の登録済み数字リストを取得."""
        statement = (
            select(Voiceprint.digit)
            .where(Voiceprint.speaker_id == speaker_id)
            .where(Voiceprint.digit != None)  # noqa: E711
            .distinct()
        )
        result = self.session.exec(statement).all()
        return sorted([d for d in result if d is not None])

    def get_by_public_id(self, public_id: str) -> Voiceprint | None:
        statement = select(Voiceprint).where(Voiceprint.public_id == public_id)
        return self.session.exec(statement).first()

    def delete_by_speaker_id(self, speaker_id: int) -> int:
        """話者のすべての声紋を削除."""
        voiceprints = self.get_by_speaker_id(speaker_id)
        count = len(voiceprints)
        for vp in voiceprints:
            self.session.delete(vp)
        self.session.commit()
        return count
