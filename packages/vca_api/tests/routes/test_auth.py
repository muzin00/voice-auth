from fastapi.testclient import TestClient
from vca_core.models import Speaker


class TestAuthRegister:
    """POST /api/v1/auth/register のテスト."""

    def test_register_speaker(self, client: TestClient):
        """話者登録（基本ケース）."""
        request_data = {
            "speaker_id": "speaker_001",
            "speaker_name": "山田太郎",
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_001"
        assert data["speaker_name"] == "山田太郎"
        assert "voice_sample_id" in data
        assert "voiceprint_id" in data
        assert "passphrase" in data
        assert data["status"] == "registered"

    def test_register_speaker_without_name(self, client: TestClient):
        """話者名なしで登録."""
        request_data = {
            "speaker_id": "speaker_002",
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_002"
        assert data["speaker_name"] is None

    def test_register_speaker_with_audio_format(self, client: TestClient):
        """audio_formatを指定して登録."""
        request_data = {
            "speaker_id": "speaker_003",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "wav",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_003"
        assert data["status"] == "registered"

    def test_register_speaker_with_data_url(self, client: TestClient):
        """Data URL形式で登録."""
        request_data = {
            "speaker_id": "speaker_004",
            "audio_data": "data:audio/wav;base64,SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_004"

    def test_register_speaker_missing_speaker_id(self, client: TestClient):
        """speaker_idなしでエラー."""
        request_data = {
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 422  # Validation Error

    def test_register_speaker_missing_audio_data(self, client: TestClient):
        """audio_dataなしでエラー."""
        request_data = {
            "speaker_id": "speaker_005",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 422  # Validation Error

    def test_register_speaker_invalid_audio_format(self, client: TestClient):
        """無効なaudio_formatでエラー."""
        request_data = {
            "speaker_id": "speaker_006",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "invalid",
        }

        response = client.post("/api/v1/auth/register", json=request_data)

        assert response.status_code == 422  # Validation Error


class TestAuthVerify:
    """POST /api/v1/auth/verify のテスト."""

    def test_verify_speaker_success(
        self, client: TestClient, registered_speaker: Speaker
    ):
        """認証成功: パスフレーズ一致."""
        request_data = {
            "speaker_id": registered_speaker.speaker_id,
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["speaker_id"] == registered_speaker.speaker_id
        assert data["authenticated"] is True
        assert data["passphrase_match"] is True
        assert "voice_similarity" in data
        assert "detected_passphrase" in data
        assert data["detected_passphrase"] == "mock_passphrase"
        assert "message" in data

    def test_verify_speaker_with_audio_format(
        self, client: TestClient, registered_speaker: Speaker
    ):
        """audio_formatを指定して認証."""
        request_data = {
            "speaker_id": registered_speaker.speaker_id,
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "wav",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["speaker_id"] == registered_speaker.speaker_id
        assert data["authenticated"] is True
        assert data["detected_passphrase"] == "mock_passphrase"

    def test_verify_speaker_not_found(self, client: TestClient):
        """存在しない話者でエラー."""
        request_data = {
            "speaker_id": "nonexistent_speaker",
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_verify_speaker_missing_speaker_id(self, client: TestClient):
        """speaker_idなしでエラー."""
        request_data = {
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 422  # Validation Error

    def test_verify_speaker_missing_audio_data(self, client: TestClient):
        """audio_dataなしでエラー."""
        request_data = {
            "speaker_id": "speaker_001",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 422  # Validation Error

    def test_verify_speaker_invalid_audio_format(self, client: TestClient):
        """無効なaudio_formatでエラー."""
        request_data = {
            "speaker_id": "speaker_001",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "invalid",
        }

        response = client.post("/api/v1/auth/verify", json=request_data)

        assert response.status_code == 422  # Validation Error
