"""WebSocket認証エンドポイントのテスト."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from vca_api.main import app


@pytest.fixture(name="ws_client")
def ws_client_fixture():
    """WebSocketテスト用クライアント."""
    return TestClient(app)


class TestVerifyWebSocket:
    """認証WebSocketエンドポイントのテスト."""

    def test_connection_requires_speaker_id(self, ws_client: TestClient):
        """speaker_idが必須であること."""
        # speaker_idなしで接続するとWebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect("/ws/verify"):
                pass

    def test_connection_sends_challenge(self, ws_client: TestClient):
        """接続時にチャレンジが送信されること."""
        with ws_client.websocket_connect(
            "/ws/verify?speaker_id=test_speaker"
        ) as websocket:
            data = websocket.receive_json()

            assert data["type"] == "challenge"
            assert data["speaker_id"] == "test_speaker"
            assert "challenge" in data
            assert len(data["challenge"]) == 4
            assert data["challenge"].isdigit()
            assert data["max_retries"] == 3

    def test_audio_returns_verify_result(self, ws_client: TestClient):
        """音声送信で認証結果が返ること（スタブモード）."""
        with ws_client.websocket_connect(
            "/ws/verify?speaker_id=test_speaker"
        ) as websocket:
            # チャレンジ受信
            challenge_data = websocket.receive_json()
            assert challenge_data["type"] == "challenge"

            # 音声データ送信（スタブなので空でもOK）
            websocket.send_bytes(b"\x00" * 1000)

            # 認証結果受信
            result_data = websocket.receive_json()

            assert result_data["type"] == "verify_result"
            assert result_data["success"] is True  # スタブモードでは常に成功
            assert result_data["speaker_id"] == "test_speaker"
            assert "similarity" in result_data
            assert "asr_result" in result_data

    def test_session_ends_after_success(self, ws_client: TestClient):
        """認証成功後にセッションが終了すること."""
        with ws_client.websocket_connect(
            "/ws/verify?speaker_id=test_speaker"
        ) as websocket:
            # チャレンジ受信
            websocket.receive_json()

            # 音声データ送信
            websocket.send_bytes(b"\x00" * 1000)

            # 認証結果受信
            result_data = websocket.receive_json()
            assert result_data["success"] is True

            # セッションが終了しているので、追加の送信は不要
