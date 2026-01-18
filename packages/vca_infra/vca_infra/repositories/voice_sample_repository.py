from sqlmodel import Session, select
from vca_core.models import VoiceSample


class VoiceSampleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        speaker_id: int,
        audio_file_path: str,
        audio_format: str,
        sample_rate: int | None = None,
        channels: int | None = None,
    ) -> VoiceSample:
        voice_sample = VoiceSample(
            speaker_id=speaker_id,
            audio_file_path=audio_file_path,
            audio_format=audio_format,
            sample_rate=sample_rate,
            channels=channels,
        )
        self.session.add(voice_sample)
        self.session.commit()
        self.session.refresh(voice_sample)
        return voice_sample

    def get_by_id(self, voice_sample_id: int) -> VoiceSample | None:
        return self.session.get(VoiceSample, voice_sample_id)

    def get_by_public_id(self, public_id: str) -> VoiceSample | None:
        statement = select(VoiceSample).where(VoiceSample.public_id == public_id)
        return self.session.exec(statement).first()
