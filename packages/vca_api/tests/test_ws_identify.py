"""WebSocket識別エンドポイントのテスト."""

import pytest
from fastapi.testclient import TestClient
from vca_api.main import app


@pytest.fixture(name="ws_client")
def ws_client_fixture():
    """WebSocketテスト用クライアント."""
    return TestClient(app)


class TestIdentifyWebSocket:
    """識別WebSocketエンドポイントのテスト."""

    def test_connection_sends_challenge(self, ws_client: TestClient):
        """接続時にチャレンジが送信されること."""
        with ws_client.websocket_connect("/ws/identify") as websocket:
            data = websocket.receive_json()

            assert data["type"] == "challenge"
            assert "challenge" in data
            assert len(data["challenge"]) == 4
            assert data["challenge"].isdigit()
            assert data["max_retries"] == 3

    def test_audio_returns_identify_result(self, ws_client: TestClient):
        """音声送信で識別結果が返ること（スタブモード）."""
        with ws_client.websocket_connect("/ws/identify") as websocket:
            # チャレンジ受信
            challenge_data = websocket.receive_json()
            assert challenge_data["type"] == "challenge"

            # 音声データ送信（スタブなので空でもOK）
            websocket.send_bytes(b"\x00" * 1000)

            # 識別結果受信
            result_data = websocket.receive_json()

            assert result_data["type"] == "identify_result"
            assert result_data["success"] is True  # スタブモードでは常に成功
            assert "asr_result" in result_data
            assert "candidates" in result_data
            assert len(result_data["candidates"]) > 0

            # 候補の形式確認
            candidate = result_data["candidates"][0]
            assert "speaker_id" in candidate
            assert "similarity" in candidate

    def test_session_ends_after_success(self, ws_client: TestClient):
        """識別成功後にセッションが終了すること."""
        with ws_client.websocket_connect("/ws/identify") as websocket:
            # チャレンジ受信
            websocket.receive_json()

            # 音声データ送信
            websocket.send_bytes(b"\x00" * 1000)

            # 識別結果受信
            result_data = websocket.receive_json()
            assert result_data["success"] is True
