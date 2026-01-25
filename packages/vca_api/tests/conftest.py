from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from vca_api.dependencies.storage import get_storage
from vca_api.main import app
from vca_core.models import Speaker
from vca_core.services.auth_service import VoiceprintServiceProtocol
from vca_infra.repositories import SpeakerRepository
from vca_infra.session import get_session
from vca_infra.storages import LocalStorage


class MockVoiceprintService(VoiceprintServiceProtocol):
    """テスト用のモック声紋サービス."""

    def extract(self, audio_bytes: bytes, audio_format: str = "wav") -> bytes:
        """モック声紋抽出."""
        return b"\x00" * 192 * 4  # 192次元 * 4バイト(float32)

    def compare(self, embedding1: bytes, embedding2: bytes) -> float:
        """モック声紋比較."""
        # 常に高い類似度を返す（テスト成功用）
        return 0.95


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


@pytest.fixture(name="voiceprint_service")
def voiceprint_service_fixture() -> MockVoiceprintService:
    """テスト用のモック声紋サービス."""
    return MockVoiceprintService()


@pytest.fixture(name="client")
def client_fixture(
    session: Session,
    storage: LocalStorage,
    voiceprint_service: MockVoiceprintService,
):
    """テスト用クライアント（依存性オーバーライド付き）."""
    from vca_api.dependencies.auth import get_auth_service
    from vca_core.services.auth_service import AuthService
    from vca_infra.repositories import (
        SpeakerRepository,
        VoiceprintRepository,
        VoiceSampleRepository,
    )
    from vca_infra.settings import voiceprint_settings

    def get_session_override():
        return session

    def get_storage_override():
        return storage

    def get_auth_service_override():
        speaker_repository = SpeakerRepository(session)
        voice_sample_repository = VoiceSampleRepository(session)
        voiceprint_repository = VoiceprintRepository(session)

        return AuthService(
            speaker_repository=speaker_repository,
            voice_sample_repository=voice_sample_repository,
            voiceprint_repository=voiceprint_repository,
            storage=storage,
            voiceprint_service=voiceprint_service,
            voice_similarity_threshold=voiceprint_settings.VOICEPRINT_SIMILARITY_THRESHOLD,
        )

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_storage] = get_storage_override
    app.dependency_overrides[get_auth_service] = get_auth_service_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="registered_speaker")
def registered_speaker_fixture(session: Session) -> Speaker:
    """登録済み話者を作成するfixture."""
    from vca_infra.repositories import VoiceprintRepository

    speaker_repo = SpeakerRepository(session)
    voiceprint_repo = VoiceprintRepository(session)

    # 話者を作成
    speaker = speaker_repo.create(
        Speaker(speaker_id="test_speaker", speaker_name="テスト話者")
    )
    assert speaker.id is not None

    # 声紋を登録（MockVoiceprintServiceが返すダミー声紋）
    voiceprint_repo.create(
        speaker_id=speaker.id,
        voice_sample_id=1,  # ダミー値
        embedding=b"\x00" * 192 * 4,  # 192次元 * 4バイト(float32)
    )

    return speaker
