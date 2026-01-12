from collections.abc import Generator

from sqlmodel import Session, create_engine

from vca_store.settings import db_settings

engine = create_engine(
    db_settings.database_url,
    echo=db_settings.ECHO,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
