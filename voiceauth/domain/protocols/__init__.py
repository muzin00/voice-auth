"""Domain protocols."""

from voiceauth.domain.protocols.asr import ASRProtocol, ASRResult, TokenInfo
from voiceauth.domain.protocols.audio import AudioConverterProtocol
from voiceauth.domain.protocols.store import SpeakerStoreProtocol
from voiceauth.domain.protocols.vad import VADProtocol
from voiceauth.domain.protocols.voiceprint import VoiceprintProtocol

__all__ = [
    "ASRProtocol",
    "ASRResult",
    "TokenInfo",
    "AudioConverterProtocol",
    "SpeakerStoreProtocol",
    "VADProtocol",
    "VoiceprintProtocol",
]
