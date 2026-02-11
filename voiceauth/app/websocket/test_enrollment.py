"""Tests for WebSocket enrollment endpoint."""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from voiceauth.app.main import create_app


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_audio_processor():
    """Create mock audio processor."""
    processor = MagicMock()
    processor.process_webm.return_value = (np.zeros(16000, dtype=np.float32), 16000)

    # Mock processing result
    mock_result = MagicMock()
    mock_result.asr_text = "1234567890"
    mock_result.digits = "1234567890"
    mock_result.digit_embeddings = {
        str(d): np.random.randn(192).astype(np.float32) for d in range(10)
    }
    processor.process_enrollment_audio.return_value = mock_result

    return processor


@pytest.fixture
def mock_speaker_store():
    """Create mock speaker store."""
    store = MagicMock()
    store.speaker_exists.return_value = False
    store.create_speaker.return_value = MagicMock()
    store.add_voiceprints_bulk.return_value = []
    return store


class TestEnrollmentWebSocket:
    """Tests for /ws/enrollment endpoint."""

    def test_successful_enrollment_flow(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test complete successful enrollment flow."""
        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            # Setup mock database session
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                # Step 1: Send start_enrollment
                websocket.send_text(
                    json.dumps(
                        {
                            "type": "start_enrollment",
                            "speaker_id": "test-speaker-001",
                            "speaker_name": "Test User",
                        }
                    )
                )

                # Step 2: Receive prompts
                data = json.loads(websocket.receive_text())
                assert data["type"] == "prompts"
                assert data["speaker_id"] == "test-speaker-001"
                assert len(data["prompts"]) == 5
                assert data["current_set"] == 0

                # Step 3: Send audio for each prompt (5 sets)
                for i in range(5):
                    websocket.send_bytes(b"fake-webm-audio-data")
                    data = json.loads(websocket.receive_text())
                    assert data["type"] == "asr_result"
                    assert data["success"] is True
                    assert data["set_index"] == i

                # Step 4: Send PIN
                websocket.send_text(json.dumps({"type": "register_pin", "pin": "1234"}))

                # Step 5: Receive enrollment complete
                data = json.loads(websocket.receive_text())
                assert data["type"] == "enrollment_complete"
                assert data["speaker_id"] == "test-speaker-001"
                assert data["has_pin"] is True
                assert data["status"] == "registered"

    def test_enrollment_without_pin(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test enrollment without PIN."""
        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                # Start enrollment
                websocket.send_text(
                    json.dumps(
                        {"type": "start_enrollment", "speaker_id": "test-speaker-002"}
                    )
                )

                # Receive prompts
                data = json.loads(websocket.receive_text())
                assert data["type"] == "prompts"

                # Send audio for each prompt
                for _ in range(5):
                    websocket.send_bytes(b"fake-webm-audio-data")
                    websocket.receive_text()

                # Send empty PIN
                websocket.send_text(json.dumps({"type": "register_pin", "pin": ""}))

                # Receive enrollment complete
                data = json.loads(websocket.receive_text())
                assert data["type"] == "enrollment_complete"
                assert data["has_pin"] is False

    def test_speaker_already_exists(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test error when speaker already exists."""
        mock_speaker_store.speaker_exists.return_value = True

        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                websocket.send_text(
                    json.dumps(
                        {
                            "type": "start_enrollment",
                            "speaker_id": "existing-speaker",
                        }
                    )
                )

                data = json.loads(websocket.receive_text())
                assert data["type"] == "error"
                assert data["code"] == "SPEAKER_ALREADY_EXISTS"

    def test_invalid_first_message(self, client):
        """Test error when first message is not start_enrollment."""
        with client.websocket_connect("/ws/enrollment") as websocket:
            websocket.send_text(
                json.dumps({"type": "some_other_type", "speaker_id": "test"})
            )

            data = json.loads(websocket.receive_text())
            assert data["type"] == "error"
            assert data["code"] == "INVALID_MESSAGE"

    def test_invalid_json_message(self, client):
        """Test error when message is not valid JSON."""
        with client.websocket_connect("/ws/enrollment") as websocket:
            websocket.send_text("not a json message")

            data = json.loads(websocket.receive_text())
            assert data["type"] == "error"
            assert data["code"] == "INVALID_MESSAGE"

    def test_asr_failure_with_retry(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test ASR failure triggers retry."""
        # First call fails, second succeeds
        mock_result = MagicMock()
        mock_result.asr_text = "1234567890"
        mock_result.digits = "1234567890"
        mock_result.digit_embeddings = {
            str(d): np.random.randn(192).astype(np.float32) for d in range(10)
        }

        call_count = [0]

        def process_enrollment_side_effect(audio, expected_prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("ASR failed")
            return mock_result

        mock_audio_processor.process_enrollment_audio.side_effect = (
            process_enrollment_side_effect
        )

        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_enrollment", "speaker_id": "test-speaker-003"}
                    )
                )

                # Receive prompts
                data = json.loads(websocket.receive_text())
                assert data["type"] == "prompts"

                # First audio - fails
                websocket.send_bytes(b"fake-webm-audio-data")
                data = json.loads(websocket.receive_text())
                assert data["type"] == "asr_result"
                assert data["success"] is False
                assert data["retry_count"] == 1

                # Retry - succeeds
                websocket.send_bytes(b"fake-webm-audio-data")
                data = json.loads(websocket.receive_text())
                assert data["type"] == "asr_result"
                assert data["success"] is True

    def test_invalid_pin_format(self, client, mock_audio_processor, mock_speaker_store):
        """Test error for invalid PIN format."""
        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_enrollment", "speaker_id": "test-speaker-004"}
                    )
                )

                # Receive prompts
                websocket.receive_text()

                # Send audio for each prompt
                for _ in range(5):
                    websocket.send_bytes(b"fake-webm-audio-data")
                    websocket.receive_text()

                # Send invalid PIN (not 4 digits)
                websocket.send_text(json.dumps({"type": "register_pin", "pin": "12"}))

                data = json.loads(websocket.receive_text())
                assert data["type"] == "error"
                assert data["code"] == "INVALID_PIN"

    def test_unexpected_text_during_audio_phase(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test error when text is sent instead of audio."""
        with (
            patch(
                "voiceauth.app.websocket.enrollment.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.enrollment.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.enrollment.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/enrollment") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_enrollment", "speaker_id": "test-speaker-005"}
                    )
                )

                # Receive prompts
                websocket.receive_text()

                # Send text instead of binary audio
                websocket.send_text(json.dumps({"type": "unexpected"}))

                data = json.loads(websocket.receive_text())
                assert data["type"] == "error"
                assert data["code"] == "INVALID_MESSAGE"
                assert "バイナリ" in data["message"]
