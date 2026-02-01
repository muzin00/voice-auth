"""機械学習モデルのロード処理."""

import logging
from pathlib import Path

import sherpa_onnx

from vca_engine.settings import engine_settings

logger = logging.getLogger(__name__)

# モデルのシングルトンインスタンス
_speaker_extractor: sherpa_onnx.SpeakerEmbeddingExtractor | None = None
_vad: sherpa_onnx.VoiceActivityDetector | None = None
_asr: sherpa_onnx.OfflineRecognizer | None = None


def get_speaker_extractor() -> sherpa_onnx.SpeakerEmbeddingExtractor:
    """sherpa-onnx話者埋め込みエクストラクタを取得.

    Returns:
        SpeakerEmbeddingExtractor: sherpa-onnxエクストラクタインスタンス

    Raises:
        RuntimeError: モデルがロードされていない場合
    """
    if _speaker_extractor is None:
        raise RuntimeError("Speaker model not loaded. Call load_models() first.")
    return _speaker_extractor


def get_vad() -> sherpa_onnx.VoiceActivityDetector:
    """Silero VADを取得.

    Returns:
        VoiceActivityDetector: VADインスタンス

    Raises:
        RuntimeError: モデルがロードされていない場合
    """
    if _vad is None:
        raise RuntimeError("VAD model not loaded. Call load_models() first.")
    return _vad


def get_asr() -> sherpa_onnx.OfflineRecognizer:
    """SenseVoice ASRを取得.

    Returns:
        OfflineRecognizer: ASRインスタンス

    Raises:
        RuntimeError: モデルがロードされていない場合
    """
    if _asr is None:
        raise RuntimeError("ASR model not loaded. Call load_models() first.")
    return _asr


def _load_speaker_model() -> None:
    """話者埋め込みモデルをロード."""
    global _speaker_extractor

    model_path = Path(engine_settings.SPEAKER_MODEL_PATH)
    if not model_path.exists():
        logger.warning(f"Speaker model not found: {model_path}")
        return

    logger.info(
        f"Loading speaker model: {model_path} "
        f"(num_threads={engine_settings.SPEAKER_NUM_THREADS})"
    )

    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(model_path),
        num_threads=engine_settings.SPEAKER_NUM_THREADS,
        debug=False,
    )

    _speaker_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
    logger.info("Speaker model loaded successfully")


def _load_vad_model() -> None:
    """Silero VADモデルをロード."""
    global _vad

    model_path = Path(engine_settings.VAD_MODEL_PATH)
    if not model_path.exists():
        logger.warning(f"VAD model not found: {model_path}")
        return

    logger.info(f"Loading VAD model: {model_path}")

    config = sherpa_onnx.VadModelConfig(
        silero_vad=sherpa_onnx.SileroVadModelConfig(
            model=str(model_path),
            min_silence_duration=0.25,
            min_speech_duration=0.25,
        ),
        sample_rate=engine_settings.SAMPLE_RATE,
    )

    _vad = sherpa_onnx.VoiceActivityDetector(
        config,
        buffer_size_in_seconds=30,
    )
    logger.info("VAD model loaded successfully")


def _load_asr_model() -> None:
    """SenseVoice ASRモデルをロード."""
    global _asr

    model_path = Path(engine_settings.ASR_MODEL_PATH)
    tokens_path = Path(engine_settings.ASR_TOKENS_PATH)

    if not model_path.exists():
        logger.warning(f"ASR model not found: {model_path}")
        return

    if not tokens_path.exists():
        logger.warning(f"ASR tokens not found: {tokens_path}")
        return

    logger.info(
        f"Loading ASR model: {model_path} "
        f"(num_threads={engine_settings.ASR_NUM_THREADS})"
    )

    config = sherpa_onnx.OfflineRecognizerConfig(
        model_config=sherpa_onnx.OfflineModelConfig(
            sense_voice=sherpa_onnx.OfflineSenseVoiceModelConfig(
                model=str(model_path),
                language=engine_settings.ASR_LANGUAGE,
                use_itn=True,
            ),
            tokens=str(tokens_path),
            num_threads=engine_settings.ASR_NUM_THREADS,
            debug=False,
        ),
    )

    _asr = sherpa_onnx.OfflineRecognizer(config)
    logger.info("ASR model loaded successfully")


def load_models() -> None:
    """sherpa-onnxモデルをロード.

    アプリケーション起動時またはWorkerプロセス起動時に呼び出される。
    モデルのキャッシュを作成し、初回リクエストの遅延を防ぐ。
    グローバル変数にモデルインスタンスを保存してシングルトンとして管理。
    """
    _load_speaker_model()
    _load_vad_model()
    _load_asr_model()


def is_models_loaded() -> dict[str, bool]:
    """モデルのロード状態を返す."""
    return {
        "speaker": _speaker_extractor is not None,
        "vad": _vad is not None,
        "asr": _asr is not None,
    }
