"""Tests for database settings."""

from vca_infra.settings import DatabaseSettings


class TestDatabaseSettings:
    """Tests for DatabaseSettings class."""

    def test_default_sqlite_url(self) -> None:
        """Test default SQLite database URL."""
        settings = DatabaseSettings()
        assert settings.db_type == "sqlite"
        assert settings.database_url == "sqlite:///./data/vca.db"

    def test_custom_sqlite_path(self) -> None:
        """Test custom SQLite path."""
        settings = DatabaseSettings(sqlite_path="/custom/path/db.sqlite")
        assert settings.database_url == "sqlite:////custom/path/db.sqlite"

    def test_postgres_url(self) -> None:
        """Test PostgreSQL database URL."""
        settings = DatabaseSettings(
            db_type="postgres",
            postgres_server="localhost",
            postgres_port=5432,
            postgres_user="testuser",
            postgres_password="testpass",
            postgres_db="testdb",
        )
        expected = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert settings.database_url == expected

    def test_postgres_custom_port(self) -> None:
        """Test PostgreSQL with custom port."""
        settings = DatabaseSettings(
            db_type="postgres",
            postgres_server="db.example.com",
            postgres_port=5433,
            postgres_user="admin",
            postgres_password="secret",
            postgres_db="production",
        )
        expected = "postgresql://admin:secret@db.example.com:5433/production"
        assert settings.database_url == expected
