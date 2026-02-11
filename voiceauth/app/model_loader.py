"""Model loader with singleton management."""

import threading

from voiceauth.engine.asr import SenseVoiceASR
from voiceauth.engine.vad import SileroVAD
from voiceauth.engine.voiceprint import CAMPPVoiceprint


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

        self._vad: SileroVAD | None = None
        self._asr: SenseVoiceASR | None = None
        self._voiceprint: CAMPPVoiceprint | None = None
        self._vad_lock = threading.Lock()
        self._asr_lock = threading.Lock()
        self._voiceprint_lock = threading.Lock()
        self._initialized = True

    @property
    def vad(self) -> SileroVAD:
        """Get VAD model instance (lazy loaded)."""
        if self._vad is None:
            with self._vad_lock:
                if self._vad is None:
                    vad = SileroVAD()
                    vad.load()
                    self._vad = vad
        return self._vad

    @property
    def asr(self) -> SenseVoiceASR:
        """Get ASR model instance (lazy loaded)."""
        if self._asr is None:
            with self._asr_lock:
                if self._asr is None:
                    asr = SenseVoiceASR()
                    asr.load()
                    self._asr = asr
        return self._asr

    @property
    def voiceprint(self) -> CAMPPVoiceprint:
        """Get voiceprint extractor instance (lazy loaded)."""
        if self._voiceprint is None:
            with self._voiceprint_lock:
                if self._voiceprint is None:
                    extractor = CAMPPVoiceprint()
                    extractor.load()
                    self._voiceprint = extractor
        return self._voiceprint

    def preload_all(self) -> None:
        """Preload all models.

        This is useful for warming up models at application startup.
        """
        _ = self.vad
        _ = self.asr
        _ = self.voiceprint

    def is_vad_loaded(self) -> bool:
        """Check if VAD model is loaded."""
        return self._vad is not None

    def is_asr_loaded(self) -> bool:
        """Check if ASR model is loaded."""
        return self._asr is not None

    def is_voiceprint_loaded(self) -> bool:
        """Check if voiceprint model is loaded."""
        return self._voiceprint is not None

    def unload_all(self) -> None:
        """Unload all models to free memory.

        Note: After unloading, models will be reloaded on next access.
        """
        with self._vad_lock:
            self._vad = None
        with self._asr_lock:
            self._asr = None
        with self._voiceprint_lock:
            self._voiceprint = None


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


def get_vad() -> SileroVAD:
    """Get the shared VAD instance."""
    return get_model_loader().vad


def get_asr() -> SenseVoiceASR:
    """Get the shared ASR instance."""
    return get_model_loader().asr


def get_voiceprint() -> CAMPPVoiceprint:
    """Get the shared voiceprint extractor instance."""
    return get_model_loader().voiceprint
