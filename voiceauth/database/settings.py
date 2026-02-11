"""Database settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        extra="ignore",
    )

    sqlite_path: str = "./sqlite_data/voiceauth.db"

    @property
    def database_url(self) -> str:
        """Generate database URL."""
        return f"sqlite:///{self.sqlite_path}"


settings = DatabaseSettings()
