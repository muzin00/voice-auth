from typing import Protocol


class WorkerClientProtocol(Protocol):
    """Workerクライアントのプロトコル."""

    def transcribe(self, audio_bytes: bytes) -> str:
        """音声を文字起こし.

        Args:
            audio_bytes: 音声データ

        Returns:
            文字起こしテキスト（正規化済み）
        """
        ...

    def extract_voiceprint(self, audio_bytes: bytes) -> bytes:
        """声紋を抽出.

        Args:
            audio_bytes: 音声データ

        Returns:
            声紋ベクトル（256次元）
        """
        ...
