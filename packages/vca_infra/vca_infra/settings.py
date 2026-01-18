from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """データベース設定"""

    # DB種別（"postgres" or "sqlite"）
    DB_TYPE: str = "sqlite"

    # PostgreSQL設定
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "my_user"
    POSTGRES_PASSWORD: str = "my_password"
    POSTGRES_DB: str = "my_db"

    # SQLite設定
    SQLITE_PATH: str = "./data/vca.db"

    ECHO: bool = False

    @property
    def database_url(self) -> str:
        # SQLite使用時
        if self.DB_TYPE == "sqlite":
            return f"sqlite:///{self.SQLITE_PATH}"

        # Cloud SQL Proxy(Unixソケット接続)の場合
        if self.POSTGRES_SERVER.startswith("/cloudsql/"):
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@/{self.POSTGRES_DB}?host={self.POSTGRES_SERVER}"

        # 通常のPostgreSQL接続
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class StorageSettings(BaseSettings):
    """ストレージ設定"""

    STORAGE_TYPE: str = "local"
    GCS_BUCKET_NAME: str | None = None
    GCS_PROJECT_ID: str | None = None


class CelerySettings(BaseSettings):
    """Celery設定."""

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": ""}


class WhisperSettings(BaseSettings):
    """Whisperモデル設定."""

    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_LANGUAGE: str = "ja"
    WHISPER_LOCAL_FILES_ONLY: bool = True

    model_config = {"env_prefix": ""}


class WeSpeakerSettings(BaseSettings):
    """WeSpeaker設定."""

    WESPEAKER_LANG: str = "en"

    model_config = {"env_prefix": ""}


class VoiceprintSettings(BaseSettings):
    """声紋認証設定."""

    # 声紋類似度の閾値（0.0〜1.0）
    # この値以上の類似度で声紋一致と判定
    VOICEPRINT_SIMILARITY_THRESHOLD: float = 0.4

    model_config = {"env_prefix": ""}


db_settings = DatabaseSettings()
storage_settings = StorageSettings()
celery_settings = CelerySettings()
whisper_settings = WhisperSettings()
wespeaker_settings = WeSpeakerSettings()
voiceprint_settings = VoiceprintSettings()
