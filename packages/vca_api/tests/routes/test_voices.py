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
