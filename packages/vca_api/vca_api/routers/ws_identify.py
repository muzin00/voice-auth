"""識別用WebSocketエンドポイント.

/ws/identify - 1:N声紋識別フロー
"""

import logging
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from vca_auth.dto import (
    ErrorMessage,
    IdentifyCandidate,
    IdentifyChallenge,
    IdentifyResult,
)
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


class IdentifySession:
    """識別セッション管理."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.challenge = generate_challenge()
        self.retry_count = 0
        self.max_retries = 3
        self.is_identified = False
        self.identified_speaker_id: str | None = None

        # モデルのロード状態を確認
        self._models_loaded = is_models_loaded()
        self._use_stub = not all(self._models_loaded.values())
        if self._use_stub:
            logger.warning(
                f"Running in stub mode. Models loaded: {self._models_loaded}"
            )

    async def send_challenge(self) -> None:
        """チャレンジを送信."""
        message = IdentifyChallenge(
            challenge=self.challenge,
            max_retries=self.max_retries,
        )
        await self.websocket.send_json(message.to_dict())

    async def handle_audio(self, audio_data: bytes) -> None:
        """音声データを処理して識別."""
        if self._use_stub:
            # スタブモード: ダミーの候補を返す
            asr_text = self.challenge
            candidates = [
                IdentifyCandidate(speaker_id="stub_speaker_1", similarity=0.95),
                IdentifyCandidate(speaker_id="stub_speaker_2", similarity=0.85),
            ]
            self.is_identified = True
            self.identified_speaker_id = "stub_speaker_1"
            message = "識別成功（スタブモード）"
        else:
            # 実際のASR処理
            result = process_audio(audio_data)
            asr_text = normalize_asr_text(result.asr_text)
            logger.info(f"ASR result: '{result.asr_text}' -> '{asr_text}'")

            # チャレンジと照合
            if asr_text != self.challenge:
                self.retry_count += 1
                result_msg = IdentifyResult(
                    success=False,
                    asr_result=asr_text,
                    candidates=[],
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
                result_msg = IdentifyResult(
                    success=False,
                    asr_result=asr_text,
                    candidates=[],
                    retry_count=self.retry_count,
                    max_retries=self.max_retries,
                    message="声紋を抽出できませんでした",
                )
                await self.websocket.send_json(result_msg.to_dict())
                return

            # 1:N識別
            with get_session_context() as session:
                speaker_repo = SpeakerRepository(session)
                voiceprint_repo = VoiceprintRepository(session)
                service = VerificationService(speaker_repo, voiceprint_repo)
                results = service.identify(self.challenge, embeddings, top_k=3)

            candidates = [
                IdentifyCandidate(speaker_id=s.speaker_id, similarity=sim)
                for s, sim in results
            ]

            if candidates and candidates[0].similarity >= 0.6:
                self.is_identified = True
                self.identified_speaker_id = candidates[0].speaker_id
                message = f"識別成功: {candidates[0].speaker_id}"
            else:
                message = "一致する話者が見つかりませんでした"

        result_msg = IdentifyResult(
            success=self.is_identified,
            asr_result=asr_text,
            candidates=candidates,
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


@router.websocket("/ws/identify")
async def identify_websocket(websocket: WebSocket):
    """声紋識別WebSocketエンドポイント.

    Args:
        websocket: WebSocket接続

    Protocol:
        1. 接続時: サーバーからチャレンジ（4桁の数字）を送信
        2. クライアント: 音声をバイナリで送信
        3. サーバー: ASR→声紋照合→候補リストを返却
        4. 失敗時は最大3回までリトライ可能
    """
    await websocket.accept()

    session = IdentifySession(websocket)
    logger.info("Identify session started")

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

                # 識別成功または最大リトライ数に達したら終了
                if session.is_identified or session.is_max_retries_exceeded:
                    break
            elif "text" in message:
                # JSONメッセージは無視（識別フローでは使用しない）
                pass

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error in identify session: {e}")
        try:
            await session.send_error("INTERNAL_ERROR", str(e))
        except Exception:
            pass
    finally:
        result = session.identified_speaker_id or "not identified"
        logger.info(f"Identify session ended: result={result}")
