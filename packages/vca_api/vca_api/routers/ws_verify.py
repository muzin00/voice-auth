"""認証用WebSocketエンドポイント.

/ws/verify - 1:1声紋認証フロー
"""

import logging
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from vca_auth.dto import ErrorMessage, VerifyChallenge, VerifyResult
from vca_auth.repositories import SpeakerRepository, VoiceprintRepository
from vca_auth.services.verification_service import (
    VerificationService,
    generate_challenge,
)
from vca_engine import extract_digit_embeddings, is_models_loaded, process_audio
from vca_infra.database import get_session_context

logger = logging.getLogger(__name__)

router = APIRouter()


def normalize_asr_text(text: str) -> str:
    """ASRテキストを正規化."""
    text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return re.sub(r"[^0-9]", "", text)


class VerifySession:
    """認証セッション管理."""

    def __init__(self, websocket: WebSocket, speaker_id: str):
        self.websocket = websocket
        self.speaker_id = speaker_id
        self.challenge = generate_challenge()
        self.retry_count = 0
        self.max_retries = 3
        self.is_verified = False

        # モデルのロード状態を確認
        self._models_loaded = is_models_loaded()
        self._use_stub = not all(self._models_loaded.values())
        if self._use_stub:
            logger.warning(
                f"Running in stub mode. Models loaded: {self._models_loaded}"
            )

    async def send_challenge(self) -> None:
        """チャレンジを送信."""
        message = VerifyChallenge(
            speaker_id=self.speaker_id,
            challenge=self.challenge,
            max_retries=self.max_retries,
        )
        await self.websocket.send_json(message.to_dict())

    async def handle_audio(self, audio_data: bytes) -> None:
        """音声データを処理して認証."""
        if self._use_stub:
            # スタブモード: 常に成功
            asr_text = self.challenge
            is_verified = True
            similarity = 0.95
            message = "認証成功（スタブモード）"
        else:
            # 実際のASR処理
            result = process_audio(audio_data)
            asr_text = normalize_asr_text(result.asr_text)
            logger.info(f"ASR result: '{result.asr_text}' -> '{asr_text}'")

            # チャレンジと照合
            if asr_text != self.challenge:
                self.retry_count += 1
                result_msg = VerifyResult(
                    success=False,
                    speaker_id=self.speaker_id,
                    similarity=0.0,
                    asr_result=asr_text,
                    retry_count=self.retry_count,
                    max_retries=self.max_retries,
                    message=f"発話内容が一致しません (期待: {self.challenge}, 認識: {asr_text})",
                )
                await self.websocket.send_json(result_msg.to_dict())
                return

            # 声紋を抽出
            embeddings = extract_digit_embeddings(audio_data, self.challenge)
            if not embeddings:
                self.retry_count += 1
                result_msg = VerifyResult(
                    success=False,
                    speaker_id=self.speaker_id,
                    similarity=0.0,
                    asr_result=asr_text,
                    retry_count=self.retry_count,
                    max_retries=self.max_retries,
                    message="声紋を抽出できませんでした",
                )
                await self.websocket.send_json(result_msg.to_dict())
                return

            # 1:1照合
            with get_session_context() as session:
                speaker_repo = SpeakerRepository(session)
                voiceprint_repo = VoiceprintRepository(session)
                service = VerificationService(speaker_repo, voiceprint_repo)
                is_verified, similarity, message = service.verify(
                    self.speaker_id,
                    self.challenge,
                    embeddings,
                )

        self.is_verified = is_verified

        if is_verified:
            result_msg = VerifyResult(
                success=True,
                speaker_id=self.speaker_id,
                similarity=similarity,
                asr_result=asr_text,
                retry_count=self.retry_count,
                max_retries=self.max_retries,
                message=message,
            )
        else:
            self.retry_count += 1
            result_msg = VerifyResult(
                success=False,
                speaker_id=self.speaker_id,
                similarity=similarity,
                asr_result=asr_text,
                retry_count=self.retry_count,
                max_retries=self.max_retries,
                message=message,
            )

        await self.websocket.send_json(result_msg.to_dict())

    async def send_error(self, code: str, message: str) -> None:
        """エラーメッセージを送信."""
        error = ErrorMessage(code=code, message=message)
        await self.websocket.send_json(error.to_dict())

    @property
    def is_max_retries_exceeded(self) -> bool:
        """リトライ上限に達したか."""
        return self.retry_count >= self.max_retries


@router.websocket("/ws/verify")
async def verify_websocket(websocket: WebSocket, speaker_id: str):
    """声紋認証WebSocketエンドポイント.

    Args:
        websocket: WebSocket接続
        speaker_id: 認証対象の話者ID（必須）

    Protocol:
        1. 接続時: サーバーからチャレンジ（4桁の数字）を送信
        2. クライアント: 音声をバイナリで送信
        3. サーバー: ASR→声紋照合→結果を返却
        4. 失敗時は最大3回までリトライ可能
    """
    await websocket.accept()

    session = VerifySession(websocket, speaker_id)
    logger.info(f"Verify session started: speaker_id={speaker_id}")

    try:
        # チャレンジ送信
        await session.send_challenge()

        # メッセージループ
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message:
                await session.handle_audio(message["bytes"])

                # 認証成功または最大リトライ数に達したら終了
                if session.is_verified or session.is_max_retries_exceeded:
                    break
            elif "text" in message:
                # JSONメッセージは無視（認証フローでは使用しない）
                pass

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {speaker_id}")
    except Exception as e:
        logger.error(f"Error in verify session: {e}")
        try:
            await session.send_error("INTERNAL_ERROR", str(e))
        except Exception:
            pass
    finally:
        result = "verified" if session.is_verified else "failed"
        logger.info(f"Verify session ended: {speaker_id}, result={result}")
