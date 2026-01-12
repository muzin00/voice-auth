from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from vca_api.dependencies.voice import get_storage
from vca_api.main import app
from vca_store.session import get_session
from vca_store.storages import LocalStorage


@pytest.fixture(name="session")
def session_fixture():
    """テスト用のインメモリデータベースセッション."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="storage")
def storage_fixture(tmp_path: Path) -> LocalStorage:
    """テスト用のローカルストレージ."""
    return LocalStorage(base_path=str(tmp_path / "voices"))


@pytest.fixture(name="client")
def client_fixture(session: Session, storage: LocalStorage):
    """テスト用クライアント（依存性オーバーライド付き）."""

    def get_session_override():
        return session

    def get_storage_override():
        return storage

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_storage] = get_storage_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
