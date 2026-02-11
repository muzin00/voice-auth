"""Tests for WebSocket verify endpoint."""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from voiceauth.app.main import create_app
from voiceauth.domain.models import Speaker


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
    return processor


@pytest.fixture
def mock_speaker_store():
    """Create mock speaker store."""
    store = MagicMock()
    store.speaker_exists.return_value = True

    # Create mock speaker with PIN
    mock_speaker = MagicMock(spec=Speaker)
    mock_speaker.speaker_id = "test-speaker-001"
    mock_speaker.speaker_name = "Test User"
    # SHA-256 hash of "1234"
    mock_speaker.pin_hash = (
        "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
    )
    store.get_speaker_by_id.return_value = mock_speaker

    # Create mock voiceprints
    store.get_voiceprints.return_value = {
        str(d): np.random.randn(192).astype(np.float32) for d in range(10)
    }

    return store


def create_mock_verification_result(
    asr_text: str,
    asr_matched: bool,
    authenticated: bool,
    digit_scores: dict[str, float] | None = None,
    average_score: float = 0.0,
):
    """Create a mock verification result."""
    result = MagicMock()
    result.asr_text = asr_text
    result.asr_matched = asr_matched
    result.authenticated = authenticated
    result.digit_scores = digit_scores or {}
    result.average_score = average_score
    return result


class TestVerifyWebSocket:
    """Tests for /ws/verify endpoint."""

    def test_successful_voice_verification(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test complete successful voice verification flow."""
        # Setup successful verification result
        mock_audio_processor.verify_audio.return_value = create_mock_verification_result(
            asr_text="1234",
            asr_matched=True,
            authenticated=True,
            digit_scores={"1": 0.95, "2": 0.92, "3": 0.88, "4": 0.91},
            average_score=0.915,
        )

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                # Step 1: Send start_verify
                websocket.send_text(
                    json.dumps(
                        {
                            "type": "start_verify",
                            "speaker_id": "test-speaker-001",
                        }
                    )
                )

                # Step 2: Receive prompt
                data = json.loads(websocket.receive_text())
                assert data["type"] == "prompt"
                assert "prompt" in data
                assert len(data["prompt"]) == data["length"]

                # Step 3: Send audio
                websocket.send_bytes(b"fake-webm-audio-data")

                # Step 4: Receive verification result
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is True
                assert data["auth_method"] == "voice"
                assert data["asr_matched"] is True

    def test_voice_failed_pin_fallback_success(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test voice verification fails but PIN fallback succeeds."""
        # Setup failed voice verification
        mock_audio_processor.verify_audio.return_value = create_mock_verification_result(
            asr_text="1234",
            asr_matched=True,
            authenticated=False,
            digit_scores={"1": 0.65, "2": 0.62, "3": 0.58, "4": 0.61},
            average_score=0.615,
        )

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                # Start verification
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "test-speaker-001"}
                    )
                )

                # Receive prompt
                data = json.loads(websocket.receive_text())
                assert data["type"] == "prompt"

                # Send audio
                websocket.send_bytes(b"fake-webm-audio-data")

                # Receive failed voice verification with PIN fallback
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is False
                assert data["can_fallback_to_pin"] is True

                # Send correct PIN
                websocket.send_text(
                    json.dumps({"type": "verify_pin", "pin": "1234"})
                )

                # Receive PIN verification success
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is True
                assert data["auth_method"] == "pin"

    def test_asr_mismatch(self, client, mock_audio_processor, mock_speaker_store):
        """Test verification fails when ASR doesn't match prompt."""
        # Setup ASR mismatch
        mock_audio_processor.verify_audio.return_value = create_mock_verification_result(
            asr_text="5678",  # Different from prompt
            asr_matched=False,
            authenticated=False,
        )

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "test-speaker-001"}
                    )
                )

                # Receive prompt
                websocket.receive_text()

                # Send audio
                websocket.send_bytes(b"fake-webm-audio-data")

                # Receive verification result
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is False
                assert data["asr_matched"] is False

    def test_speaker_not_found(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test error when speaker doesn't exist."""
        mock_speaker_store.speaker_exists.return_value = False

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "unknown-speaker"}
                    )
                )

                data = json.loads(websocket.receive_text())
                assert data["type"] == "error"
                assert data["code"] == "SPEAKER_NOT_FOUND"

    def test_invalid_first_message(self, client):
        """Test error when first message is not start_verify."""
        with client.websocket_connect("/ws/verify") as websocket:
            websocket.send_text(
                json.dumps({"type": "some_other_type", "speaker_id": "test"})
            )

            data = json.loads(websocket.receive_text())
            assert data["type"] == "error"
            assert data["code"] == "INVALID_MESSAGE"

    def test_invalid_json_message(self, client):
        """Test error when message is not valid JSON."""
        with client.websocket_connect("/ws/verify") as websocket:
            websocket.send_text("not a json message")

            data = json.loads(websocket.receive_text())
            assert data["type"] == "error"
            assert data["code"] == "INVALID_MESSAGE"

    def test_text_instead_of_audio(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test error when text is sent instead of audio."""
        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "test-speaker-001"}
                    )
                )

                # Receive prompt
                websocket.receive_text()

                # Send text instead of binary audio
                websocket.send_text(json.dumps({"type": "unexpected"}))

                data = json.loads(websocket.receive_text())
                assert data["type"] == "error"
                assert data["code"] == "INVALID_MESSAGE"
                assert "バイナリ" in data["message"] or "音声" in data["message"]

    def test_pin_verification_failed(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test PIN verification fails with wrong PIN."""
        # Setup failed voice verification
        mock_audio_processor.verify_audio.return_value = create_mock_verification_result(
            asr_text="1234",
            asr_matched=True,
            authenticated=False,
            digit_scores={"1": 0.65, "2": 0.62, "3": 0.58, "4": 0.61},
            average_score=0.615,
        )

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "test-speaker-001"}
                    )
                )

                # Receive prompt
                websocket.receive_text()

                # Send audio
                websocket.send_bytes(b"fake-webm-audio-data")

                # Receive failed voice verification
                data = json.loads(websocket.receive_text())
                assert data["can_fallback_to_pin"] is True

                # Send wrong PIN
                websocket.send_text(
                    json.dumps({"type": "verify_pin", "pin": "9999"})
                )

                # Receive PIN verification failure
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is False
                # Can still retry
                assert data["can_fallback_to_pin"] is True

    def test_speaker_without_pin_no_fallback(
        self, client, mock_audio_processor, mock_speaker_store
    ):
        """Test no PIN fallback when speaker has no PIN."""
        # Speaker without PIN
        mock_speaker = MagicMock(spec=Speaker)
        mock_speaker.speaker_id = "test-speaker-002"
        mock_speaker.pin_hash = None
        mock_speaker_store.get_speaker_by_id.return_value = mock_speaker

        # Setup failed voice verification
        mock_audio_processor.verify_audio.return_value = create_mock_verification_result(
            asr_text="1234",
            asr_matched=True,
            authenticated=False,
            digit_scores={"1": 0.65, "2": 0.62, "3": 0.58, "4": 0.61},
            average_score=0.615,
        )

        with (
            patch(
                "voiceauth.app.websocket.verify.get_audio_processor",
                return_value=mock_audio_processor,
            ),
            patch("voiceauth.app.websocket.verify.Session") as mock_session_class,
            patch(
                "voiceauth.app.websocket.verify.SpeakerStore",
                return_value=mock_speaker_store,
            ),
        ):
            mock_db_session = MagicMock()
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_db_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            with client.websocket_connect("/ws/verify") as websocket:
                websocket.send_text(
                    json.dumps(
                        {"type": "start_verify", "speaker_id": "test-speaker-002"}
                    )
                )

                # Receive prompt
                websocket.receive_text()

                # Send audio
                websocket.send_bytes(b"fake-webm-audio-data")

                # Receive failed voice verification without PIN fallback
                data = json.loads(websocket.receive_text())
                assert data["type"] == "verify_result"
                assert data["authenticated"] is False
                assert "can_fallback_to_pin" not in data or data.get("can_fallback_to_pin") is False
