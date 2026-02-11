"""Database settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings.

    Supports both SQLite and PostgreSQL backends.
    """

    model_config = SettingsConfigDict(
        env_prefix="VOICEAUTH_DB_",
        env_file=".env",
        extra="ignore",
    )

    db_type: str = "sqlite"  # "sqlite" or "postgres"
    sqlite_path: str = "./data/voiceauth.db"
    postgres_server: str = ""
    postgres_port: int = Field(default=5432)
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""

    @property
    def database_url(self) -> str:
        """Generate database URL based on db_type."""
        if self.db_type == "postgres":
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
            )
        # Default to SQLite
        return f"sqlite:///{self.sqlite_path}"


settings = DatabaseSettings()
