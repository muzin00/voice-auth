"""Model loader with singleton management."""

import threading

from .asr import SpeechRecognizer
from .vad import VoiceActivityDetector
from .voiceprint import VoiceprintExtractor


class ModelLoader:
    """Singleton manager for ML models.

    This class ensures models are loaded only once and provides
    thread-safe access to shared model instances.
    """

    _instance: "ModelLoader | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._vad: VoiceActivityDetector | None = None
        self._asr: SpeechRecognizer | None = None
        self._speaker: VoiceprintExtractor | None = None
        self._vad_lock = threading.Lock()
        self._asr_lock = threading.Lock()
        self._speaker_lock = threading.Lock()
        self._initialized = True

    @property
    def vad(self) -> VoiceActivityDetector:
        """Get VAD model instance (lazy loaded)."""
        if self._vad is None:
            with self._vad_lock:
                if self._vad is None:
                    vad = VoiceActivityDetector()
                    vad.load()
                    self._vad = vad
        return self._vad

    @property
    def asr(self) -> SpeechRecognizer:
        """Get ASR model instance (lazy loaded)."""
        if self._asr is None:
            with self._asr_lock:
                if self._asr is None:
                    asr = SpeechRecognizer()
                    asr.load()
                    self._asr = asr
        return self._asr

    @property
    def speaker(self) -> VoiceprintExtractor:
        """Get voiceprint extractor instance (lazy loaded)."""
        if self._speaker is None:
            with self._speaker_lock:
                if self._speaker is None:
                    extractor = VoiceprintExtractor()
                    extractor.load()
                    self._speaker = extractor
        return self._speaker

    def preload_all(self) -> None:
        """Preload all models.

        This is useful for warming up models at application startup.
        """
        _ = self.vad
        _ = self.asr
        _ = self.speaker

    def is_vad_loaded(self) -> bool:
        """Check if VAD model is loaded."""
        return self._vad is not None

    def is_asr_loaded(self) -> bool:
        """Check if ASR model is loaded."""
        return self._asr is not None

    def is_speaker_loaded(self) -> bool:
        """Check if speaker model is loaded."""
        return self._speaker is not None

    def unload_all(self) -> None:
        """Unload all models to free memory.

        Note: After unloading, models will be reloaded on next access.
        """
        with self._vad_lock:
            self._vad = None
        with self._asr_lock:
            self._asr = None
        with self._speaker_lock:
            self._speaker = None


# Global model loader instance
_loader: ModelLoader | None = None
_loader_lock = threading.Lock()


def get_model_loader() -> ModelLoader:
    """Get the global model loader instance."""
    global _loader
    if _loader is None:
        with _loader_lock:
            if _loader is None:
                _loader = ModelLoader()
    return _loader


def get_vad() -> VoiceActivityDetector:
    """Get the shared VAD instance."""
    return get_model_loader().vad


def get_asr() -> SpeechRecognizer:
    """Get the shared ASR instance."""
    return get_model_loader().asr


def get_voiceprint_extractor() -> VoiceprintExtractor:
    """Get the shared voiceprint extractor instance."""
    return get_model_loader().speaker
