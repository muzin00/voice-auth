"""Database settings for VCA infrastructure."""

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings.

    Supports both SQLite and PostgreSQL backends.
    """

    db_type: str = "sqlite"  # "sqlite" or "postgres"
    sqlite_path: str = "./data/vca.db"
    postgres_server: str = ""
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""

    model_config = {"env_prefix": "VCA_DB_"}

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


db_settings = DatabaseSettings()
