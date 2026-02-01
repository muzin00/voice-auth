"""API settings configuration."""

from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """Settings for the VCA API server."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    debug: bool = False
    websocket_timeout: int = 60  # seconds

    model_config = {"env_prefix": "VCA_API_"}


settings = APISettings()
