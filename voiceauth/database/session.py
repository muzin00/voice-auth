"""Database session management."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from voiceauth.database.settings import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        SQLModel Session instance.
    """
    with Session(engine) as session:
        yield session
