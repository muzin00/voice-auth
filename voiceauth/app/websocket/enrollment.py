"""WebSocket endpoint for speaker enrollment."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from voiceauth.database import SpeakerStore
from voiceauth.database.session import engine
from voiceauth.domain_service import (
    EnrollmentService,
    EnrollmentSession,
    EnrollmentState,
    SpeakerAlreadyExistsError,
)

from ..settings import settings

# Placeholder for audio processor - will be injected
# This is a simplified version; actual implementation would use proper DI
router = APIRouter()


class StartEnrollmentMessage(BaseModel):
    """Message to start enrollment."""

    type: str  # "start_enrollment"
    speaker_id: str
    speaker_name: str | None = None


class RegisterPINMessage(BaseModel):
    """Message to register PIN."""

    type: str  # "register_pin"
    pin: str


def create_error_response(code: str, message: str) -> dict[str, Any]:
    """Create error response message."""
    return {"type": "error", "code": code, "message": message}


def create_prompts_response(
    speaker_id: str,
    prompts: list[str],
    current_set: int,
) -> dict[str, Any]:
    """Create prompts response message."""
    return {
        "type": "prompts",
        "speaker_id": speaker_id,
        "prompts": prompts,
        "total_sets": len(prompts),
        "current_set": current_set,
    }


def create_asr_result_response(
    success: bool,
    asr_result: str,
    set_index: int,
    remaining_sets: int,
    message: str,
    retry_count: int = 0,
    max_retries: int = 5,
) -> dict[str, Any]:
    """Create ASR result response message."""
    response: dict[str, Any] = {
        "type": "asr_result",
        "success": success,
        "asr_result": asr_result,
        "set_index": set_index,
        "remaining_sets": remaining_sets,
        "message": message,
    }
    if not success:
        response["retry_count"] = retry_count
        response["max_retries"] = max_retries
    return response


def create_enrollment_complete_response(
    speaker_id: str,
    has_pin: bool,
) -> dict[str, Any]:
    """Create enrollment complete response message."""
    return {
        "type": "enrollment_complete",
        "speaker_id": speaker_id,
        "has_pin": has_pin,
        "status": "registered",
    }


async def send_json(websocket: WebSocket, data: dict[str, Any]) -> None:
    """Send JSON message through WebSocket."""
    await websocket.send_text(json.dumps(data, ensure_ascii=False))


def get_audio_processor() -> Any:
    """Get audio processor instance.

    Note: This is a placeholder. The actual implementation
    would use proper dependency injection.
    """
    # Import here to avoid circular imports
    from voiceauth.app.model_loader import get_asr, get_vad, get_voiceprint
    from voiceauth.audio import AudioConverter

    # Create a simple processor wrapper
    class AudioProcessorWrapper:
        def __init__(self) -> None:
            self.converter = AudioConverter()
            self.vad = get_vad()
            self.asr = get_asr()
            self.voiceprint = get_voiceprint()

        def process_webm(self, webm_data: bytes) -> tuple[Any, int]:
            return self.converter.webm_to_pcm(webm_data)

        def process_enrollment_audio(self, audio: Any, expected_prompt: str) -> Any:
            # Run ASR
            asr_result = self.asr.recognize(audio)

            # Check if recognized digits match expected
            if asr_result.normalized_text != expected_prompt:
                raise ValueError(
                    f"Expected '{expected_prompt}', got '{asr_result.normalized_text}'"
                )

            # Extract speech-only audio via VAD, then compute embedding
            speech_audio = self.vad.extract_speech(audio)
            embedding = self.voiceprint.extract(speech_audio)

            # Create result object
            class ProcessingResult:
                def __init__(
                    self, text: str, digits: str, utterance_embedding: Any
                ) -> None:
                    self._asr_text = text
                    self._digits = digits
                    self._utterance_embedding = utterance_embedding

                @property
                def asr_text(self) -> str:
                    return self._asr_text

                @property
                def digits(self) -> str:
                    return self._digits

                @property
                def utterance_embedding(self) -> Any:
                    return self._utterance_embedding

            return ProcessingResult(
                asr_result.text, asr_result.normalized_text, embedding
            )

    return AudioProcessorWrapper()


@router.websocket("/ws/enrollment")
async def enrollment_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for speaker enrollment.

    Protocol:
    1. Client connects
    2. Client sends JSON: {"type": "start_enrollment", "speaker_id": "...", ...}
    3. Server sends JSON: {"type": "prompts", "prompts": [...], ...}
    4. For each prompt (5 sets):
       4.1 Client sends Binary: WebM audio data
       4.2 Server sends JSON: {"type": "asr_result", "success": true/false, ...}
       4.3 On failure, retry with same prompt
    5. Client sends JSON: {"type": "register_pin", "pin": "1234"}
    6. Server sends JSON: {"type": "enrollment_complete", ...}
    7. Connection closes
    """
    await websocket.accept()

    session: EnrollmentSession | None = None
    enrollment_service: EnrollmentService | None = None

    try:
        # Wait for start_enrollment message with timeout
        try:
            message = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=settings.websocket_timeout,
            )
        except TimeoutError:
            await send_json(
                websocket,
                create_error_response("TIMEOUT", "タイムアウトしました"),
            )
            return

        # Parse start message
        try:
            data = json.loads(message)
            if data.get("type") != "start_enrollment":
                await send_json(
                    websocket,
                    create_error_response(
                        "INVALID_MESSAGE",
                        "最初のメッセージはstart_enrollmentである必要があります",
                    ),
                )
                return

            start_msg = StartEnrollmentMessage(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            await send_json(
                websocket,
                create_error_response("INVALID_MESSAGE", f"無効なメッセージ: {e}"),
            )
            return

        # Create enrollment service with database session
        with Session(engine) as db_session:
            speaker_store = SpeakerStore(db_session)
            audio_processor = get_audio_processor()
            enrollment_service = EnrollmentService(audio_processor, speaker_store)

            # Start enrollment
            try:
                session = enrollment_service.start_enrollment(
                    speaker_id=start_msg.speaker_id,
                    speaker_name=start_msg.speaker_name,
                )
            except SpeakerAlreadyExistsError:
                await send_json(
                    websocket,
                    create_error_response(
                        "SPEAKER_ALREADY_EXISTS",
                        f"Speaker '{start_msg.speaker_id}' は既に登録されています",
                    ),
                )
                return

            # Send prompts
            await send_json(
                websocket,
                create_prompts_response(
                    speaker_id=session.speaker_id,
                    prompts=session.prompts,
                    current_set=0,
                ),
            )

            # Process audio for each prompt set
            while session.current_set_index < len(session.prompts):
                if session.state == EnrollmentState.FAILED:
                    await send_json(
                        websocket,
                        create_error_response(
                            "ENROLLMENT_FAILED",
                            session.error_message or "登録に失敗しました",
                        ),
                    )
                    return

                # Wait for audio data
                try:
                    message = await asyncio.wait_for(
                        websocket.receive(),
                        timeout=settings.websocket_timeout,
                    )
                except TimeoutError:
                    await send_json(
                        websocket,
                        create_error_response("TIMEOUT", "タイムアウトしました"),
                    )
                    return

                # Handle binary (audio) or text (JSON) message
                if "bytes" in message:
                    audio_data = message["bytes"]

                    # Process audio
                    result = enrollment_service.process_audio(session, audio_data)

                    # Send ASR result
                    await send_json(
                        websocket,
                        create_asr_result_response(
                            success=result.success,
                            asr_result=result.asr_text,
                            set_index=result.set_index,
                            remaining_sets=result.remaining_sets,
                            message=result.message,
                            retry_count=result.retry_count,
                            max_retries=result.max_retries,
                        ),
                    )

                elif "text" in message:
                    # Unexpected text message during audio recording
                    await send_json(
                        websocket,
                        create_error_response(
                            "INVALID_MESSAGE",
                            "音声データ（バイナリ）が期待されています",
                        ),
                    )

            # Voice enrollment complete, wait for PIN
            if session.state != EnrollmentState.COMPLETED_VOICE:
                await send_json(
                    websocket,
                    create_error_response(
                        "ENROLLMENT_FAILED",
                        "音声登録が完了していません",
                    ),
                )
                return

            # Wait for PIN registration
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.websocket_timeout,
                )
            except TimeoutError:
                await send_json(
                    websocket,
                    create_error_response("TIMEOUT", "タイムアウトしました"),
                )
                return

            # Parse PIN message
            try:
                data = json.loads(message)
                if data.get("type") != "register_pin":
                    await send_json(
                        websocket,
                        create_error_response(
                            "INVALID_MESSAGE",
                            "register_pinメッセージが期待されています",
                        ),
                    )
                    return

                pin_msg = RegisterPINMessage(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                await send_json(
                    websocket,
                    create_error_response("INVALID_MESSAGE", f"無効なメッセージ: {e}"),
                )
                return

            # Complete enrollment with PIN
            try:
                result = enrollment_service.complete_enrollment(
                    session=session,
                    pin=pin_msg.pin if pin_msg.pin else None,
                )

                await send_json(
                    websocket,
                    create_enrollment_complete_response(
                        speaker_id=result.speaker_id,
                        has_pin=result.has_pin,
                    ),
                )
            except ValueError as e:
                await send_json(
                    websocket,
                    create_error_response("INVALID_PIN", str(e)),
                )
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
