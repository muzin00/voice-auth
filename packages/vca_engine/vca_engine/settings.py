from pydantic_settings import BaseSettings


class EngineSettings(BaseSettings):
    """音声エンジン設定."""

    SPEAKER_MODEL_PATH: str = "models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx"
    SPEAKER_NUM_THREADS: int = 1

    model_config = {"env_prefix": "VCA_ENGINE_"}


engine_settings = EngineSettings()
