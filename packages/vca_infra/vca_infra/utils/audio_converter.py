"""音声フォーマット変換ユーティリティ."""

import io
import logging

import av

logger = logging.getLogger(__name__)


def convert_to_wav(audio_bytes: bytes, source_format: str) -> bytes:
    """任意の音声フォーマットをWAVに変換.

    Args:
        audio_bytes: 音声データ（任意のフォーマット）
        source_format: 元のフォーマット（webm, mp3, m4a等）

    Returns:
        WAV形式の音声データ（16bit PCM, モノラル）
    """
    logger.info(f"Converting {source_format} to WAV: {len(audio_bytes)} bytes")
    input_buffer = io.BytesIO(audio_bytes)
    output_buffer = io.BytesIO()

    # format=source_format を削除して自動判別に
    try:
        with av.open(input_buffer, mode="r") as in_container:
            if not in_container.streams.audio:
                raise ValueError("No audio stream found")

            with av.open(output_buffer, mode="w", format="wav") as out_container:
                # WeSpeakerが絶対条件とする 16000Hz / モノラル を指定
                out_stream = out_container.add_stream("pcm_s16le", rate=16000)
                out_stream.layout = "mono"

                # リサンプラーを作成（どんな入力も 16k/モノラル/s16 に変換する）
                resampler = av.AudioResampler(
                    format="s16",
                    layout="mono",
                    rate=16000,
                )

                for frame in in_container.decode(audio=0):
                    # 入力フレームを16kHzモノラルに変換
                    resampled_frames = resampler.resample(frame)
                    for f in resampled_frames:
                        for packet in out_stream.encode(f):
                            out_container.mux(packet)

                # フラッシュ
                for packet in out_stream.encode(None):
                    out_container.mux(packet)

        # 'with' ブロックを抜けた瞬間、WAVヘッダーが確定します
        return output_buffer.getvalue()

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise
