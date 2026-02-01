"""WebSocket登録エンドポイントのテスト."""

import pytest
from fastapi.testclient import TestClient
from vca_api.main import app


@pytest.fixture(name="ws_client")
def ws_client_fixture():
    """WebSocketテスト用クライアント."""
    return TestClient(app)


class TestEnrollmentWebSocket:
    """登録WebSocketエンドポイントのテスト."""

    def test_connection_sends_prompts(self, ws_client: TestClient):
        """接続時にプロンプトが送信されること."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            data = websocket.receive_json()

            assert data["type"] == "prompts"
            assert "speaker_id" in data
            assert "prompts" in data
            assert len(data["prompts"]) == 5
            assert data["total_sets"] == 5
            assert data["current_set"] == 0

            # 各プロンプトが4桁であること
            for prompt in data["prompts"]:
                assert len(prompt) == 4
                assert prompt.isdigit()

    def test_connection_with_speaker_id(self, ws_client: TestClient):
        """speaker_idを指定して接続."""
        with ws_client.websocket_connect(
            "/ws/enrollment?speaker_id=test123"
        ) as websocket:
            data = websocket.receive_json()

            assert data["type"] == "prompts"
            assert data["speaker_id"] == "test123"

    def test_binary_audio_returns_asr_result(self, ws_client: TestClient):
        """バイナリ音声送信でASR結果が返ること."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # プロンプト受信
            prompts_data = websocket.receive_json()
            assert prompts_data["type"] == "prompts"

            # 音声データ送信（スタブなので空でもOK）
            websocket.send_bytes(b"\x00" * 1000)

            # ASR結果受信
            asr_data = websocket.receive_json()

            assert asr_data["type"] == "asr_result"
            assert asr_data["success"] is True
            assert asr_data["set_index"] == 0
            assert "remaining_sets" in asr_data
            assert asr_data["message"] == "OK！次へ進みます"

    def test_complete_enrollment_flow(self, ws_client: TestClient):
        """登録フロー全体のテスト."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # 1. プロンプト受信
            prompts_data = websocket.receive_json()
            assert prompts_data["type"] == "prompts"
            total_sets = prompts_data["total_sets"]

            # 2. 5セット分の音声を送信
            for i in range(total_sets):
                websocket.send_bytes(b"\x00" * 1000)
                asr_data = websocket.receive_json()

                assert asr_data["type"] == "asr_result"
                assert asr_data["success"] is True
                assert asr_data["set_index"] == i

            # 3. PIN登録
            pin_request = {"type": "register_pin", "pin": "1234"}
            websocket.send_json(pin_request)

            # 4. 登録完了メッセージ受信
            complete_data = websocket.receive_json()

            assert complete_data["type"] == "enrollment_complete"
            assert complete_data["has_pin"] is True
            assert complete_data["status"] == "registered"
            assert len(complete_data["registered_digits"]) == 10

    def test_invalid_pin_format(self, ws_client: TestClient):
        """無効なPIN形式でエラー."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # プロンプト受信
            websocket.receive_json()

            # 5セット分の音声を送信
            for _ in range(5):
                websocket.send_bytes(b"\x00" * 1000)
                websocket.receive_json()

            # 無効なPIN（3桁）
            pin_request = {"type": "register_pin", "pin": "123"}
            websocket.send_json(pin_request)

            error_data = websocket.receive_json()

            assert error_data["type"] == "error"
            assert error_data["code"] == "INVALID_PIN"

    def test_pin_before_completion_returns_error(self, ws_client: TestClient):
        """セット完了前のPIN登録でエラー."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # プロンプト受信
            websocket.receive_json()

            # 1セットだけ送信
            websocket.send_bytes(b"\x00" * 1000)
            websocket.receive_json()

            # PIN登録を試みる
            pin_request = {"type": "register_pin", "pin": "1234"}
            websocket.send_json(pin_request)

            error_data = websocket.receive_json()

            assert error_data["type"] == "error"
            assert error_data["code"] == "INVALID_STATE"

    def test_invalid_json_returns_error(self, ws_client: TestClient):
        """無効なJSONでエラー."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # プロンプト受信
            websocket.receive_json()

            # 無効なJSON送信
            websocket.send_text("not valid json")

            error_data = websocket.receive_json()

            assert error_data["type"] == "error"
            assert error_data["code"] == "INVALID_JSON"

    def test_unknown_message_type_returns_error(self, ws_client: TestClient):
        """未知のメッセージタイプでエラー."""
        with ws_client.websocket_connect("/ws/enrollment") as websocket:
            # プロンプト受信
            websocket.receive_json()

            # 未知のタイプ送信
            websocket.send_json({"type": "unknown_type"})

            error_data = websocket.receive_json()

            assert error_data["type"] == "error"
            assert error_data["code"] == "UNKNOWN_MESSAGE_TYPE"
