"""登録用WebSocketエンドポイント.

/ws/enrollment - 声紋登録フロー
"""

import json
import logging
import re
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from vca_auth.dto import (
    ASRResult,
    EnrollmentComplete,
    EnrollmentPrompts,
    ErrorMessage,
    RegisterPinRequest,
)
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository
from vca_auth.services import (
    EnrollmentService,
    EnrollmentState,
    EnrollmentStatus,
    generate_balanced_prompts,
)
from vca_engine import extract_digit_embeddings, is_models_loaded, process_audio
from vca_infra.database import get_session_context

logger = logging.getLogger(__name__)

router = APIRouter()


def normalize_asr_text(text: str) -> str:
    """ASRテキストを正規化.

    数字以外の文字を除去し、全角数字を半角に変換。
    """
    # 全角数字を半角に変換
    text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    # 数字以外を除去
    return re.sub(r"[^0-9]", "", text)


class EnrollmentSession:
    """登録セッション管理."""

    def __init__(self, websocket: WebSocket, speaker_id: str | None = None):
        self.websocket = websocket
        self.state = EnrollmentState(
            speaker_id=speaker_id or str(uuid.uuid4()),
            prompts=generate_balanced_prompts(),
        )
        # モデルのロード状態を確認
        self._models_loaded = is_models_loaded()
        self._use_stub = not all(self._models_loaded.values())
        if self._use_stub:
            logger.warning(
                f"Running in stub mode. Models loaded: {self._models_loaded}"
            )

    async def send_prompts(self) -> None:
        """プロンプトを送信."""
        message = EnrollmentPrompts(
            speaker_id=self.state.speaker_id,
            prompts=self.state.prompts,
            total_sets=self.state.total_sets,
            current_set=self.state.current_set,
        )
        await self.websocket.send_json(message.to_dict())

    async def handle_audio(self, audio_data: bytes) -> None:
        """音声データを処理."""
        current_prompt = self.state.current_prompt

        if current_prompt is None:
            await self.send_error("INVALID_STATE", "No prompt available")
            return

        if self._use_stub:
            # スタブモード: 常に成功
            asr_text = current_prompt
        else:
            # 実際のASR処理
            result = process_audio(audio_data)
            asr_text = normalize_asr_text(result.asr_text)
            logger.info(f"ASR result: '{result.asr_text}' -> '{asr_text}'")

        # プロンプトと照合
        if asr_text == current_prompt:
            # 成功: 声紋を抽出して保存
            if not self._use_stub:
                embeddings = extract_digit_embeddings(audio_data, current_prompt)
                for digit, embedding in embeddings.items():
                    self.state.add_voiceprint(digit, embedding)
                logger.info(
                    f"Extracted embeddings for digits: {list(embeddings.keys())}"
                )

            self.state.advance_to_next_set()

            result_msg = ASRResult(
                success=True,
                asr_result=asr_text,
                set_index=self.state.current_set - 1,
                remaining_sets=self.state.remaining_sets + 1,
                message="OK！次へ進みます",
            )
            await self.websocket.send_json(result_msg.to_dict())

            if self.state.status == EnrollmentStatus.WAITING_PIN:
                logger.info(f"All sets completed for speaker {self.state.speaker_id}")
        else:
            # 失敗
            can_retry = self.state.increment_retry()

            result_msg = ASRResult(
                success=False,
                asr_result=asr_text,
                set_index=self.state.current_set,
                retry_count=self.state.retry_count,
                max_retries=self.state.max_retries,
                message="聞き取れませんでした。もう一度、はっきりとお願いします",
            )
            await self.websocket.send_json(result_msg.to_dict())

            if not can_retry:
                await self.send_error(
                    "MAX_RETRIES_EXCEEDED",
                    "リトライ回数の上限に達しました",
                )

    async def handle_json(self, data: dict) -> None:
        """JSONメッセージを処理."""
        msg_type = data.get("type")

        if msg_type == "register_pin":
            await self.handle_register_pin(data)
        else:
            await self.send_error("UNKNOWN_MESSAGE_TYPE", f"Unknown type: {msg_type}")

    async def handle_register_pin(self, data: dict) -> None:
        """PIN登録を処理."""
        if self.state.status != EnrollmentStatus.WAITING_PIN:
            await self.send_error(
                "INVALID_STATE",
                "PIN登録は全セット完了後に行ってください",
            )
            return

        request = RegisterPinRequest.from_dict(data)
        pin = request.pin

        # PIN検証（4桁の数字）
        if not pin or len(pin) != 4 or not pin.isdigit():
            await self.send_error("INVALID_PIN", "PINは4桁の数字である必要があります")
            return

        self.state.set_pin(pin)

        # 登録済み数字を取得
        if self._use_stub:
            registered_digits = list("0123456789")
        else:
            registered_digits = self.state.registered_digits
            # データベースに保存
            self._save_to_database()

        # 登録完了メッセージ送信
        complete = EnrollmentComplete(
            speaker_id=self.state.speaker_id,
            registered_digits=registered_digits,
            has_pin=True,
            status="registered",
        )
        await self.websocket.send_json(complete.to_dict())

        logger.info(
            f"Enrollment completed for speaker {self.state.speaker_id}, "
            f"registered digits: {registered_digits}"
        )

    def _save_to_database(self) -> None:
        """登録状態をデータベースに保存."""
        try:
            with get_session_context() as session:
                speaker_repo = SpeakerRepository(session)
                voiceprint_repo = VoiceprintRepository(session)
                service = EnrollmentService(speaker_repo, voiceprint_repo)
                service.save_enrollment(self.state)
                logger.info(f"Saved enrollment to database: {self.state.speaker_id}")
        except Exception as e:
            logger.error(f"Failed to save enrollment: {e}")

    async def send_error(self, code: str, message: str) -> None:
        """エラーメッセージを送信."""
        error = ErrorMessage(code=code, message=message)
        await self.websocket.send_json(error.to_dict())


@router.websocket("/ws/enrollment")
async def enrollment_websocket(websocket: WebSocket, speaker_id: str | None = None):
    """声紋登録WebSocketエンドポイント.

    Args:
        websocket: WebSocket接続
        speaker_id: 話者ID（省略時は自動生成）

    Protocol:
        1. 接続時: サーバーからプロンプト（4桁×5セット）を送信
        2. クライアント: 各セットの音声をバイナリで送信
        3. サーバー: ASR結果を返却（成功/失敗）
        4. 全セット完了後: クライアントがPINをJSON送信
        5. サーバー: 登録完了メッセージを送信
    """
    await websocket.accept()

    session = EnrollmentSession(websocket, speaker_id)
    logger.info(f"Enrollment session started: {session.state.speaker_id}")

    try:
        # プロンプト送信
        await session.send_prompts()

        # メッセージループ
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message:
                # バイナリ = 音声データ
                await session.handle_audio(message["bytes"])
            elif "text" in message:
                # テキスト = JSONメッセージ
                try:
                    data = json.loads(message["text"])
                    await session.handle_json(data)
                except json.JSONDecodeError:
                    await session.send_error("INVALID_JSON", "Invalid JSON format")

            # 登録完了なら終了
            if session.state.status == EnrollmentStatus.COMPLETED:
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session.state.speaker_id}")
    except Exception as e:
        logger.error(f"Error in enrollment session: {e}")
        try:
            await session.send_error("INTERNAL_ERROR", str(e))
        except Exception:
            pass
    finally:
        logger.info(f"Enrollment session ended: {session.state.speaker_id}")
