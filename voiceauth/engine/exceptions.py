"""Engine exceptions."""


class EngineError(Exception):
    """Base exception for engine."""

    pass


class ModelNotLoadedError(EngineError):
    """Model is not loaded."""

    pass


class AudioConversionError(EngineError):
    """Failed to convert audio format."""

    pass


class VADError(EngineError):
    """Voice Activity Detection error."""

    pass


class ASRError(EngineError):
    """Automatic Speech Recognition error."""

    pass


class SpeakerEmbeddingError(EngineError):
    """Speaker embedding extraction error."""

    pass


class SegmentationError(EngineError):
    """Audio segmentation error."""

    pass


class NoSpeechDetectedError(VADError):
    """No speech detected in audio."""

    pass


class AudioTooShortError(EngineError):
    """Audio is too short for processing."""

    pass


class AudioTooLongError(EngineError):
    """Audio is too long for processing."""

    pass
