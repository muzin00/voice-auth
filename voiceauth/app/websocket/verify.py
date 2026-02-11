"""WebSocket endpoint for speaker verification."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from voiceauth.database import SpeakerStore
from voiceauth.database.session import engine
from voiceauth.domain_service import (
    SpeakerNotFoundError,
    VerifyService,
    VerifySession,
    VerifyState,
)

from ..settings import settings

router = APIRouter()


class StartVerifyMessage(BaseModel):
    """Message to start verification."""

    type: str  # "start_verify"
    speaker_id: str


class VerifyPINMessage(BaseModel):
    """Message to verify PIN."""

    type: str  # "verify_pin"
    pin: str


def create_error_response(code: str, message: str) -> dict[str, Any]:
    """Create error response message."""
    return {"type": "error", "code": code, "message": message}


def create_prompt_response(prompt: str) -> dict[str, Any]:
    """Create prompt response message."""
    return {
        "type": "prompt",
        "prompt": prompt,
        "length": len(prompt),
    }


def create_verify_result_response(
    authenticated: bool,
    speaker_id: str,
    asr_result: str,
    asr_matched: bool,
    voice_similarity: float | None,
    digit_scores: dict[str, float] | None,
    can_fallback_to_pin: bool,
    auth_method: str | None,
    message: str,
) -> dict[str, Any]:
    """Create verification result response message."""
    response: dict[str, Any] = {
        "type": "verify_result",
        "authenticated": authenticated,
        "speaker_id": speaker_id,
        "asr_result": asr_result,
        "asr_matched": asr_matched,
        "voice_similarity": voice_similarity,
        "digit_scores": digit_scores,
        "message": message,
    }

    if can_fallback_to_pin and not authenticated:
        response["can_fallback_to_pin"] = True

    if auth_method:
        response["auth_method"] = auth_method

    return response


async def send_json(websocket: WebSocket, data: dict[str, Any]) -> None:
    """Send JSON message through WebSocket."""
    await websocket.send_text(json.dumps(data, ensure_ascii=False))


def get_audio_processor() -> Any:
    """Get audio processor instance.

    Note: This is a placeholder. The actual implementation
    would use proper dependency injection.
    """
    from voiceauth.app.model_loader import get_asr, get_vad, get_voiceprint
    from voiceauth.audio import AudioConverter
    from voiceauth.engine.voiceprint import cosine_similarity

    class AudioProcessorWrapper:
        def __init__(self) -> None:
            self.converter = AudioConverter()
            self.vad = get_vad()
            self.asr = get_asr()
            self.voiceprint = get_voiceprint()
            self.similarity_threshold = 0.75

        def process_webm(self, webm_data: bytes) -> tuple[Any, int]:
            return self.converter.webm_to_pcm(webm_data)

        def verify_audio(
            self,
            audio: Any,
            expected_prompt: str,
            registered_embeddings: dict[str, Any],
        ) -> Any:
            from voiceauth.engine.asr import extract_digit_timestamps, segment_by_timestamps

            # Run ASR
            asr_result = self.asr.recognize(audio)

            # Check if recognized digits match expected
            asr_matched = asr_result.normalized_text == expected_prompt

            if not asr_matched:
                class VerificationResult:
                    def __init__(self) -> None:
                        self._asr_text = asr_result.normalized_text
                        self._asr_matched = False
                        self._digit_scores: dict[str, float] = {}
                        self._average_score = 0.0
                        self._authenticated = False

                    @property
                    def asr_text(self) -> str:
                        return self._asr_text

                    @property
                    def asr_matched(self) -> bool:
                        return self._asr_matched

                    @property
                    def digit_scores(self) -> dict[str, float]:
                        return self._digit_scores

                    @property
                    def average_score(self) -> float:
                        return self._average_score

                    @property
                    def authenticated(self) -> bool:
                        return self._authenticated

                return VerificationResult()

            # Get timestamps and segment
            timestamps = extract_digit_timestamps(asr_result)
            segments = segment_by_timestamps(audio, timestamps)

            # Compare embeddings
            digit_scores: dict[str, float] = {}
            for seg in segments:
                if seg.digit in registered_embeddings:
                    embedding = self.voiceprint.extract(seg.audio)
                    score = cosine_similarity(embedding, registered_embeddings[seg.digit])
                    digit_scores[seg.digit] = float(score)

            # Calculate average score
            if digit_scores:
                average_score = sum(digit_scores.values()) / len(digit_scores)
            else:
                average_score = 0.0

            authenticated = average_score >= self.similarity_threshold

            class VerificationResult:
                def __init__(
                    self,
                    text: str,
                    matched: bool,
                    scores: dict[str, float],
                    avg: float,
                    auth: bool,
                ) -> None:
                    self._asr_text = text
                    self._asr_matched = matched
                    self._digit_scores = scores
                    self._average_score = avg
                    self._authenticated = auth

                @property
                def asr_text(self) -> str:
                    return self._asr_text

                @property
                def asr_matched(self) -> bool:
                    return self._asr_matched

                @property
                def digit_scores(self) -> dict[str, float]:
                    return self._digit_scores

                @property
                def average_score(self) -> float:
                    return self._average_score

                @property
                def authenticated(self) -> bool:
                    return self._authenticated

            return VerificationResult(
                asr_result.normalized_text,
                asr_matched,
                digit_scores,
                average_score,
                authenticated,
            )

    return AudioProcessorWrapper()


@router.websocket("/ws/verify")
async def verify_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for speaker verification.

    Protocol:
    1. Client connects
    2. Client sends JSON: {"type": "start_verify", "speaker_id": "..."}
    3. Server sends JSON: {"type": "prompt", "prompt": "4326", "length": 4}
    4. Client sends Binary: WebM audio data
    5. Server sends JSON: {"type": "verify_result", ...}
    6. If voice failed and PIN available:
       6.1 Client sends JSON: {"type": "verify_pin", "pin": "1234"}
       6.2 Server sends JSON: {"type": "verify_result", ...}
    7. Connection closes
    """
    await websocket.accept()

    session: VerifySession | None = None
    verify_service: VerifyService | None = None

    try:
        # Wait for start_verify message with timeout
        try:
            message = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=settings.websocket_timeout,
            )
        except asyncio.TimeoutError:
            await send_json(
                websocket,
                create_error_response("TIMEOUT", "タイムアウトしました"),
            )
            return

        # Parse start message
        try:
            data = json.loads(message)
            if data.get("type") != "start_verify":
                await send_json(
                    websocket,
                    create_error_response(
                        "INVALID_MESSAGE",
                        "最初のメッセージはstart_verifyである必要があります",
                    ),
                )
                return

            start_msg = StartVerifyMessage(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            await send_json(
                websocket,
                create_error_response("INVALID_MESSAGE", f"無効なメッセージ: {e}"),
            )
            return

        # Create verify service with database session
        with Session(engine) as db_session:
            speaker_store = SpeakerStore(db_session)
            audio_processor = get_audio_processor()
            verify_service = VerifyService(audio_processor, speaker_store)

            # Start verification
            try:
                session = verify_service.start_verification(
                    speaker_id=start_msg.speaker_id,
                )
            except SpeakerNotFoundError:
                await send_json(
                    websocket,
                    create_error_response(
                        "SPEAKER_NOT_FOUND",
                        f"Speaker '{start_msg.speaker_id}' は登録されていません",
                    ),
                )
                return

            # Send prompt
            await send_json(
                websocket,
                create_prompt_response(session.prompt),
            )

            # Wait for audio data
            try:
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=settings.websocket_timeout,
                )
            except asyncio.TimeoutError:
                await send_json(
                    websocket,
                    create_error_response("TIMEOUT", "タイムアウトしました"),
                )
                return

            # Handle binary (audio) message
            if "bytes" not in message:
                await send_json(
                    websocket,
                    create_error_response(
                        "INVALID_MESSAGE",
                        "音声データ（バイナリ）が期待されています",
                    ),
                )
                return

            audio_data = message["bytes"]

            # Verify voice
            result = verify_service.verify_voice(session, audio_data)

            # Send verification result
            await send_json(
                websocket,
                create_verify_result_response(
                    authenticated=result.authenticated,
                    speaker_id=result.speaker_id,
                    asr_result=result.asr_result,
                    asr_matched=result.asr_matched,
                    voice_similarity=result.voice_similarity,
                    digit_scores=result.digit_scores,
                    can_fallback_to_pin=result.can_fallback_to_pin,
                    auth_method=result.auth_method,
                    message=result.message,
                ),
            )

            # If authenticated or no PIN fallback, we're done
            if result.authenticated or not result.can_fallback_to_pin:
                return

            # Wait for PIN verification (optional)
            while session.state != VerifyState.AUTHENTICATED:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.websocket_timeout,
                    )
                except asyncio.TimeoutError:
                    await send_json(
                        websocket,
                        create_error_response("TIMEOUT", "タイムアウトしました"),
                    )
                    return

                # Parse PIN message
                try:
                    data = json.loads(message)
                    if data.get("type") != "verify_pin":
                        await send_json(
                            websocket,
                            create_error_response(
                                "INVALID_MESSAGE",
                                "verify_pinメッセージが期待されています",
                            ),
                        )
                        continue

                    pin_msg = VerifyPINMessage(**data)
                except (json.JSONDecodeError, ValidationError) as e:
                    await send_json(
                        websocket,
                        create_error_response(
                            "INVALID_MESSAGE", f"無効なメッセージ: {e}"
                        ),
                    )
                    continue

                # Verify PIN
                result = verify_service.verify_pin(session, pin_msg.pin)

                await send_json(
                    websocket,
                    create_verify_result_response(
                        authenticated=result.authenticated,
                        speaker_id=result.speaker_id,
                        asr_result=result.asr_result,
                        asr_matched=result.asr_matched,
                        voice_similarity=result.voice_similarity,
                        digit_scores=result.digit_scores,
                        can_fallback_to_pin=result.can_fallback_to_pin,
                        auth_method=result.auth_method,
                        message=result.message,
                    ),
                )

                if result.authenticated:
                    return

    except WebSocketDisconnect:
        # Client disconnected - cleanup is handled automatically
        pass
    except Exception as e:
        try:
            await send_json(
                websocket,
                create_error_response("INTERNAL_ERROR", f"内部エラー: {e}"),
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
