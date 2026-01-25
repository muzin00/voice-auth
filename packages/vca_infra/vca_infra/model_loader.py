"""機械学習モデルのロード処理."""

import logging

import sherpa_onnx

from vca_infra.settings import sherpa_onnx_settings

logger = logging.getLogger(__name__)

# モデルのシングルトンインスタンス
_speaker_extractor: sherpa_onnx.SpeakerEmbeddingExtractor | None = None


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


def load_models() -> None:
    """sherpa-onnxモデルをロード.

    アプリケーション起動時またはWorkerプロセス起動時に呼び出される。
    モデルのキャッシュを作成し、初回リクエストの遅延を防ぐ。
    グローバル変数にモデルインスタンスを保存してシングルトンとして管理。
    """
    global _speaker_extractor

    # sherpa-onnx話者埋め込みモデルのロード
    logger.info(
        f"Loading sherpa-onnx speaker model: {sherpa_onnx_settings.SPEAKER_MODEL_PATH} "
        f"(num_threads={sherpa_onnx_settings.SPEAKER_NUM_THREADS})"
    )

    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=sherpa_onnx_settings.SPEAKER_MODEL_PATH,
        num_threads=sherpa_onnx_settings.SPEAKER_NUM_THREADS,
        debug=False,
    )

    _speaker_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

    logger.info("sherpa-onnx speaker model loaded successfully")
