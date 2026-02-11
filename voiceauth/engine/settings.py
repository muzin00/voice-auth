"""Engine settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineSettings(BaseSettings):
    """Audio processing engine settings."""

    model_config = SettingsConfigDict(
        env_prefix="ENGINE_",
        env_file=".env",
        extra="ignore",
    )

    # Model paths (relative to project root)
    models_dir: Path = Path("models")

    # SenseVoice ASR settings
    sensevoice_model_dir: str = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
    sensevoice_model_file: str = "model.int8.onnx"
    sensevoice_tokens_file: str = "tokens.txt"
    asr_num_threads: int = 2
    asr_use_itn: bool = True

    # Silero VAD settings
    vad_model_file: str = "silero_vad.onnx"
    vad_threshold: float = 0.5
    vad_min_silence_duration: float = 0.5
    vad_min_speech_duration: float = 0.25
    vad_buffer_size_seconds: float = 60.0

    # CAM++ Speaker Embedding settings
    speaker_model_file: str = "3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"
    speaker_num_threads: int = 1
    speaker_similarity_threshold: float = 0.85

    # Audio settings
    target_sample_rate: int = 16000
    min_audio_duration: float = 1.0  # seconds
    max_audio_duration: float = 10.0  # seconds

    # Segmentation settings
    segment_padding_seconds: float = 0.08  # 80ms padding

    @property
    def sensevoice_model_path(self) -> Path:
        """Full path to SenseVoice model file."""
        return self.models_dir / self.sensevoice_model_dir / self.sensevoice_model_file

    @property
    def sensevoice_tokens_path(self) -> Path:
        """Full path to SenseVoice tokens file."""
        return self.models_dir / self.sensevoice_model_dir / self.sensevoice_tokens_file

    @property
    def vad_model_path(self) -> Path:
        """Full path to Silero VAD model file."""
        return self.models_dir / self.vad_model_file

    @property
    def speaker_model_path(self) -> Path:
        """Full path to CAM++ speaker model file."""
        return self.models_dir / self.speaker_model_file


settings = EngineSettings()
