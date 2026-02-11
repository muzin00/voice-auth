"""Domain protocols."""

from voiceauth.domain.protocols.asr import ASRProtocol, ASRResult, TokenInfo
from voiceauth.domain.protocols.audio import AudioConverterProtocol
from voiceauth.domain.protocols.enrollment import (
    EnrollmentAudioProcessorProtocol,
    EnrollmentSpeakerStoreProtocol,
    ProcessingResultProtocol,
)
from voiceauth.domain.protocols.store import SpeakerStoreProtocol
from voiceauth.domain.protocols.vad import VADProtocol
from voiceauth.domain.protocols.verify import (
    VerificationResultProtocol,
    VerifyAudioProcessorProtocol,
    VerifySpeakerStoreProtocol,
)
from voiceauth.domain.protocols.voiceprint import VoiceprintProtocol

__all__ = [
    "ASRProtocol",
    "ASRResult",
    "TokenInfo",
    "AudioConverterProtocol",
    "EnrollmentAudioProcessorProtocol",
    "EnrollmentSpeakerStoreProtocol",
    "ProcessingResultProtocol",
    "SpeakerStoreProtocol",
    "VADProtocol",
    "VerificationResultProtocol",
    "VerifyAudioProcessorProtocol",
    "VerifySpeakerStoreProtocol",
    "VoiceprintProtocol",
]
