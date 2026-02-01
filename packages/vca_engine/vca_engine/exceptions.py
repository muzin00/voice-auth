"""VCA Engine exceptions."""


class VCAEngineError(Exception):
    """Base exception for VCA Engine."""

    pass


class ModelNotLoadedError(VCAEngineError):
    """Model is not loaded."""

    pass


class AudioConversionError(VCAEngineError):
    """Failed to convert audio format."""

    pass


class VADError(VCAEngineError):
    """Voice Activity Detection error."""

    pass


class ASRError(VCAEngineError):
    """Automatic Speech Recognition error."""

    pass


class SpeakerEmbeddingError(VCAEngineError):
    """Speaker embedding extraction error."""

    pass


class SegmentationError(VCAEngineError):
    """Audio segmentation error."""

    pass


class NoSpeechDetectedError(VADError):
    """No speech detected in audio."""

    pass


class AudioTooShortError(VCAEngineError):
    """Audio is too short for processing."""

    pass


class AudioTooLongError(VCAEngineError):
    """Audio is too long for processing."""

    pass
