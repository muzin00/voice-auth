"""API settings configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Settings for the VoiceAuth API server."""

    model_config = SettingsConfigDict(
        env_prefix="VOICEAUTH_API_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = "info"
    debug: bool = False
    websocket_timeout: int = 60  # seconds


settings = APISettings()
