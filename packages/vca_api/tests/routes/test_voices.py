import pytest
from fastapi.testclient import TestClient
from vca_api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestVoiceRegistration:
    def test_register_voice(self, client: TestClient):
        request_data = {
            "speaker_id": "speaker_001",
            "speaker_name": "山田太郎",
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert "voice_id" in data
        assert data["speaker_id"] == "speaker_001"
        assert data["speaker_name"] == "山田太郎"
        assert data["status"] == "registered"

    def test_register_voice_without_speaker_name(self, client: TestClient):
        request_data = {
            "speaker_id": "speaker_002",
            "audio_data": "SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_002"
        assert data["speaker_name"] is None

    def test_register_voice_with_audio_format(self, client: TestClient):
        """audio_formatを指定した音声登録."""
        request_data = {
            "speaker_id": "speaker_003",
            "speaker_name": "山田太郎",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "mp3",
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_003"
        assert data["status"] == "registered"

    def test_register_voice_with_sample_rate(self, client: TestClient):
        """sample_rateを指定した音声登録."""
        request_data = {
            "speaker_id": "speaker_004",
            "audio_data": "SGVsbG8gV29ybGQh",
            "sample_rate": 44100,
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_004"
        assert data["status"] == "registered"

    def test_register_voice_with_channels(self, client: TestClient):
        """channelsを指定した音声登録."""
        request_data = {
            "speaker_id": "speaker_005",
            "audio_data": "SGVsbG8gV29ybGQh",
            "channels": 1,
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_005"
        assert data["status"] == "registered"

    def test_register_voice_with_all_optional_fields(self, client: TestClient):
        """すべてのオプションフィールドを指定した音声登録."""
        request_data = {
            "speaker_id": "speaker_006",
            "speaker_name": "山田太郎",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "wav",
            "sample_rate": 48000,
            "channels": 2,
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_006"
        assert data["speaker_name"] == "山田太郎"
        assert data["status"] == "registered"

    def test_register_voice_with_data_url(self, client: TestClient):
        """Data URL形式のaudio_dataを使用した音声登録."""
        request_data = {
            "speaker_id": "speaker_007",
            "speaker_name": "山田太郎",
            "audio_data": "data:audio/wav;base64,SGVsbG8gV29ybGQh",
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_007"
        assert data["speaker_name"] == "山田太郎"
        assert data["status"] == "registered"

    def test_register_voice_with_webm_format(self, client: TestClient):
        """WebM形式の音声登録（Web Audio API想定）."""
        request_data = {
            "speaker_id": "speaker_008",
            "audio_data": "data:audio/webm;base64,SGVsbG8gV29ybGQh",
            "audio_format": "webm",
            "sample_rate": 48000,
            "channels": 1,
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_008"
        assert data["status"] == "registered"

    def test_register_voice_with_aac_format(self, client: TestClient):
        """AAC形式の音声登録（Flutter想定）."""
        request_data = {
            "speaker_id": "speaker_009",
            "speaker_name": "山田太郎",
            "audio_data": "SGVsbG8gV29ybGQh",
            "audio_format": "aac",
            "sample_rate": 44100,
            "channels": 1,
        }

        response = client.post("/api/v1/voices/register", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["speaker_id"] == "speaker_009"
        assert data["speaker_name"] == "山田太郎"
        assert data["status"] == "registered"
