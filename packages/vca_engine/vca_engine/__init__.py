"""VCA Engine - Voice Cognition Authentication audio processing package.

This package provides:
- Audio format conversion (WebM to PCM)
- Voice Activity Detection (Silero VAD)
- Automatic Speech Recognition (SenseVoice)
- Speaker Embedding Extraction (CAM++)
- Audio Segmentation

Usage:
    from vca_engine import get_processor

    processor = get_processor()

    # Process enrollment audio
    result = processor.process_enrollment_audio(audio, "4326")
    print(f"Recognized: {result.digits}")
    print(f"Embeddings: {list(result.digit_embeddings.keys())}")

    # Verify audio
    verification = processor.verify_audio(audio, "4326", registered_embeddings)
    print(f"Authenticated: {verification.authenticated}")
"""

from .asr import ASRResult, SpeechRecognizer, TokenInfo, extract_digit_timestamps
from .audio_converter import (
    ensure_mono,
    load_wav_file,
    resample_audio,
    webm_to_pcm,
)
from .audio_processor import (
    AudioProcessor,
    ProcessingResult,
    VerificationResult,
    get_processor,
)
from .exceptions import (
    ASRError,
    AudioConversionError,
    AudioTooLongError,
    AudioTooShortError,
    ModelNotLoadedError,
    NoSpeechDetectedError,
    SegmentationError,
    SpeakerEmbeddingError,
    VADError,
    VCAEngineError,
)
from .model_loader import (
    get_asr,
    get_model_loader,
    get_vad,
    get_voiceprint_extractor,
)
from .segmentation import (
    DigitSegment,
    cut_segment_with_padding,
    get_segment_duration,
    merge_segments,
    segment_by_timestamps,
)
from .settings import EngineSettings, settings
from .vad import VoiceActivityDetector
from .voiceprint import (
    VoiceprintExtractor,
    compute_centroid,
    cosine_similarity,
    is_same_voiceprint,
)

__all__ = [
    # Settings
    "EngineSettings",
    "settings",
    # Exceptions
    "VCAEngineError",
    "ModelNotLoadedError",
    "AudioConversionError",
    "VADError",
    "ASRError",
    "SpeakerEmbeddingError",
    "SegmentationError",
    "NoSpeechDetectedError",
    "AudioTooShortError",
    "AudioTooLongError",
    # Converter
    "webm_to_pcm",
    "load_wav_file",
    "resample_audio",
    "ensure_mono",
    # VAD
    "VoiceActivityDetector",
    # ASR
    "SpeechRecognizer",
    "ASRResult",
    "TokenInfo",
    "extract_digit_timestamps",
    # Voiceprint
    "VoiceprintExtractor",
    "cosine_similarity",
    "compute_centroid",
    "is_same_voiceprint",
    # Segmentation
    "DigitSegment",
    "cut_segment_with_padding",
    "segment_by_timestamps",
    "merge_segments",
    "get_segment_duration",
    # Loader
    "get_model_loader",
    "get_vad",
    "get_asr",
    "get_voiceprint_extractor",
    # Processor (Facade)
    "AudioProcessor",
    "ProcessingResult",
    "VerificationResult",
    "get_processor",
]
