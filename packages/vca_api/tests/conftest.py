from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from vca_api.dependencies.storage import get_storage
from vca_api.dependencies.worker import get_worker_client
from vca_api.main import app
from vca_core.interfaces.worker_client import WorkerClientProtocol
from vca_core.models import Speaker
from vca_infra.repositories import PassphraseRepository, SpeakerRepository
from vca_infra.session import get_session
from vca_infra.storages import LocalStorage


class MockWorkerClient(WorkerClientProtocol):
    """テスト用のモックWorkerClient."""

    def transcribe(self, audio_bytes: bytes) -> str:
        """モック文字起こし."""
        return "mock_passphrase"

    def extract_voiceprint(self, audio_bytes: bytes) -> bytes:
        """モック声紋抽出."""
        return b"\x00" * 256 * 4


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


@pytest.fixture(name="worker_client")
def worker_client_fixture() -> MockWorkerClient:
    """テスト用のモックWorkerClient."""
    return MockWorkerClient()


@pytest.fixture(name="client")
def client_fixture(
    session: Session, storage: LocalStorage, worker_client: MockWorkerClient
):
    """テスト用クライアント（依存性オーバーライド付き）."""

    def get_session_override():
        return session

    def get_storage_override():
        return storage

    def get_worker_client_override():
        return worker_client

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_storage] = get_storage_override
    app.dependency_overrides[get_worker_client] = get_worker_client_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="registered_speaker")
def registered_speaker_fixture(session: Session) -> Speaker:
    """登録済み話者を作成するfixture."""
    speaker_repo = SpeakerRepository(session)
    passphrase_repo = PassphraseRepository(session)

    # 話者を作成
    speaker = speaker_repo.create(
        Speaker(speaker_id="test_speaker", speaker_name="テスト話者")
    )
    assert speaker.id is not None

    # パスフレーズを登録（mock_passphraseはMockWorkerClientが返す値）
    passphrase_repo.create(
        speaker_id=speaker.id,
        voice_sample_id=1,  # ダミー値
        phrase="mock_passphrase",
    )

    return speaker
