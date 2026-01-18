"""機械学習モデルのロード処理."""

import logging
from typing import Any

import wespeakerruntime as wespeaker
from faster_whisper import WhisperModel

from vca_infra.settings import wespeaker_settings, whisper_settings

logger = logging.getLogger(__name__)

# モデルのシングルトンインスタンス
_whisper_model: WhisperModel | None = None
_speaker_model: Any | None = None


def get_whisper_model() -> WhisperModel:
    """Whisperモデルを取得.

    Returns:
        WhisperModel: Whisperモデルインスタンス

    Raises:
        RuntimeError: モデルがロードされていない場合
    """
    if _whisper_model is None:
        raise RuntimeError("Whisper model not loaded. Call load_models() first.")
    return _whisper_model


def get_speaker_model() -> Any:
    """WeSpeaker話者モデルを取得.

    Returns:
        Speaker: WeSpeakerモデルインスタンス

    Raises:
        RuntimeError: モデルがロードされていない場合
    """
    if _speaker_model is None:
        raise RuntimeError("Speaker model not loaded. Call load_models() first.")
    return _speaker_model


def load_models() -> None:
    """WhisperとWeSpeakerモデルをロード.

    アプリケーション起動時またはWorkerプロセス起動時に呼び出される。
    モデルのキャッシュを作成し、初回リクエストの遅延を防ぐ。
    グローバル変数にモデルインスタンスを保存してシングルトンとして管理。
    """
    global _whisper_model, _speaker_model

    # Whisperモデルのロード
    logger.info(
        f"Loading Whisper model: {whisper_settings.WHISPER_MODEL_SIZE} "
        f"(device={whisper_settings.WHISPER_DEVICE}, "
        f"compute_type={whisper_settings.WHISPER_COMPUTE_TYPE}, "
        f"local_files_only={whisper_settings.WHISPER_LOCAL_FILES_ONLY})"
    )

    _whisper_model = WhisperModel(
        whisper_settings.WHISPER_MODEL_SIZE,
        device=whisper_settings.WHISPER_DEVICE,
        compute_type=whisper_settings.WHISPER_COMPUTE_TYPE,
        local_files_only=whisper_settings.WHISPER_LOCAL_FILES_ONLY,
    )

    logger.info("Whisper model loaded successfully")

    # WeSpeakerモデルのロード
    logger.info(f"Loading WeSpeaker model: lang={wespeaker_settings.WESPEAKER_LANG}")

    _speaker_model = wespeaker.Speaker(lang=wespeaker_settings.WESPEAKER_LANG)

    logger.info("WeSpeaker model loaded successfully")
