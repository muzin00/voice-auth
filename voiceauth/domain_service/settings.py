"""Domain service settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DomainServiceSettings(BaseSettings):
    """Domain service configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        env_file=".env",
        extra="ignore",
    )

    # Enrollment settings
    enrollment_max_retries: int = 5

    # Verification settings
    verification_prompt_length: int = 4
    similarity_threshold: float = 0.85


settings = DomainServiceSettings()
