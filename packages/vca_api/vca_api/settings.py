"""API settings configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """Settings for the VCA API server."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = "info"
    debug: bool = False
    websocket_timeout: int = 60  # seconds

    model_config = {"env_prefix": "VCA_API_"}


settings = APISettings()
