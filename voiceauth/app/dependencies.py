"""Dependency injection for FastAPI."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from voiceauth.audio import AudioConverter
from voiceauth.database import SpeakerStore, get_session
from voiceauth.domain_service import EnrollmentService, VerifyService
from voiceauth.engine.asr import SenseVoiceASR
from voiceauth.engine.vad import SileroVAD
from voiceauth.engine.voiceprint import CAMPPVoiceprint

from .model_loader import get_asr, get_vad, get_voiceprint


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    yield from get_session()


def get_audio_converter() -> AudioConverter:
    """Get audio converter instance."""
    return AudioConverter()


def get_vad_instance() -> SileroVAD:
    """Get VAD instance."""
    return get_vad()


def get_asr_instance() -> SenseVoiceASR:
    """Get ASR instance."""
    return get_asr()


def get_voiceprint_instance() -> CAMPPVoiceprint:
    """Get voiceprint instance."""
    return get_voiceprint()


def get_speaker_store(
    session: Annotated[Session, Depends(get_db)],
) -> SpeakerStore:
    """Get speaker store with injected session."""
    return SpeakerStore(session)


# Type aliases for dependency injection
DbSession = Annotated[Session, Depends(get_db)]
AudioConverterDep = Annotated[AudioConverter, Depends(get_audio_converter)]
VADDep = Annotated[SileroVAD, Depends(get_vad_instance)]
ASRDep = Annotated[SenseVoiceASR, Depends(get_asr_instance)]
VoiceprintDep = Annotated[CAMPPVoiceprint, Depends(get_voiceprint_instance)]
SpeakerStoreDep = Annotated[SpeakerStore, Depends(get_speaker_store)]
