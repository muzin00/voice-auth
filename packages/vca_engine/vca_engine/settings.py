from pydantic_settings import BaseSettings


class EngineSettings(BaseSettings):
    """音声エンジン設定."""

    # 話者埋め込み (CAM++)
    SPEAKER_MODEL_PATH: str = "models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"
    SPEAKER_NUM_THREADS: int = 1

    # VAD (Silero)
    VAD_MODEL_PATH: str = "models/silero_vad.onnx"

    # ASR (SenseVoice)
    ASR_MODEL_PATH: str = "models/model.int8.onnx"
    ASR_TOKENS_PATH: str = "models/tokens.txt"
    ASR_NUM_THREADS: int = 2
    ASR_LANGUAGE: str = "ja"  # ja, en, zh, etc.

    # 音声設定
    SAMPLE_RATE: int = 16000

    model_config = {"env_prefix": "VCA_ENGINE_"}


engine_settings = EngineSettings()
