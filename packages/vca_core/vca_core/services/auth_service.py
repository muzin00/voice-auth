import base64
import logging
from dataclasses import dataclass
from uuid import uuid4

from vca_core.constants import MAX_AUDIO_SIZE
from vca_core.exceptions import NotFoundError
from vca_core.interfaces.passphrase_repository import PassphraseRepositoryProtocol
from vca_core.interfaces.speaker_repository import SpeakerRepositoryProtocol
from vca_core.interfaces.storage import StorageProtocol
from vca_core.interfaces.voice_sample_repository import VoiceSampleRepositoryProtocol
from vca_core.interfaces.voiceprint_repository import VoiceprintRepositoryProtocol
from vca_core.interfaces.worker_client import WorkerClientProtocol
from vca_core.models import Passphrase, Speaker, Voiceprint, VoiceSample

logger = logging.getLogger(__name__)

MAX_PASSPHRASES_PER_SPEAKER = 3


@dataclass
class AuthRegisterResult:
    """認証登録結果."""

    speaker: Speaker
    voice_sample: VoiceSample
    voiceprint: Voiceprint
    passphrase: Passphrase


@dataclass
class AuthVerifyResult:
    """認証結果（1:1照合）."""

    authenticated: bool
    speaker_id: str
    passphrase_match: bool
    voice_similarity: float
    message: str


class AuthService:
    def __init__(
        self,
        speaker_repository: SpeakerRepositoryProtocol,
        voice_sample_repository: VoiceSampleRepositoryProtocol,
        voiceprint_repository: VoiceprintRepositoryProtocol,
        passphrase_repository: PassphraseRepositoryProtocol,
        storage: StorageProtocol,
        worker_client: WorkerClientProtocol,
    ):
        self.speaker_repository = speaker_repository
        self.voice_sample_repository = voice_sample_repository
        self.voiceprint_repository = voiceprint_repository
        self.passphrase_repository = passphrase_repository
        self.storage = storage
        self.worker_client = worker_client

    def register(
        self,
        speaker_id: str,
        audio_data: str,
        audio_format: str,
        speaker_name: str | None = None,
    ) -> AuthRegisterResult:
        """話者登録（音声ファイル + パスフレーズ + 声紋）."""
        logger.info(f"Registering speaker: {speaker_id}")

        # 1. Speaker を登録または取得
        speaker = self._get_or_create_speaker(speaker_id, speaker_name)
        assert speaker.id is not None

        # 2. パスフレーズ数の上限チェック
        passphrase_count = self.passphrase_repository.count_by_speaker_id(speaker.id)
        if passphrase_count >= MAX_PASSPHRASES_PER_SPEAKER:
            raise ValueError(
                f"Maximum number of passphrases ({MAX_PASSPHRASES_PER_SPEAKER}) reached"
            )

        # 3. 音声データをデコード
        audio_bytes = self._decode_audio_data(audio_data)

        # 4. 音声ファイルをストレージに保存
        storage_path = self._save_audio_to_storage(
            speaker.id, audio_bytes, audio_format
        )

        # 5. VoiceSample をDBに保存
        voice_sample = self.voice_sample_repository.create(
            speaker_id=speaker.id,
            audio_file_path=storage_path,
            audio_format=audio_format,
        )
        assert voice_sample.id is not None
        logger.info(f"VoiceSample created: {voice_sample.public_id}")

        # 6. 文字起こし（TODO: Phase 3で実装）
        transcribed_text = self._transcribe_audio(audio_bytes, audio_format)

        # 7. 声紋抽出（TODO: Phase 3で実装）
        embedding = self._extract_voiceprint(audio_bytes, audio_format)

        # 8. Passphrase をDBに保存
        passphrase = self.passphrase_repository.create(
            speaker_id=speaker.id,
            voice_sample_id=voice_sample.id,
            phrase=transcribed_text,
        )
        logger.info(f"Passphrase created: {passphrase.public_id}")

        # 9. Voiceprint をDBに保存
        voiceprint = self.voiceprint_repository.create(
            speaker_id=speaker.id,
            voice_sample_id=voice_sample.id,
            embedding=embedding,
        )
        logger.info(f"Voiceprint created: {voiceprint.public_id}")

        return AuthRegisterResult(
            speaker=speaker,
            voice_sample=voice_sample,
            voiceprint=voiceprint,
            passphrase=passphrase,
        )

    def _get_or_create_speaker(
        self, speaker_id: str, speaker_name: str | None
    ) -> Speaker:
        """話者を取得または作成."""
        existing = self.speaker_repository.get_by_speaker_id(speaker_id)
        if existing:
            return existing
        speaker = Speaker(speaker_id=speaker_id, speaker_name=speaker_name)
        return self.speaker_repository.create(speaker)

    def _decode_audio_data(self, audio_data: str) -> bytes:
        """Base64エンコードされた音声データをデコード."""
        if audio_data.startswith("data:"):
            audio_data = audio_data.split(",", 1)[1]

        audio_bytes = base64.b64decode(audio_data)
        logger.info(f"Decoded audio: {len(audio_bytes)} bytes")

        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise ValueError(
                f"Audio size {len(audio_bytes)} bytes exceeds "
                f"maximum {MAX_AUDIO_SIZE} bytes"
            )

        return audio_bytes

    def _save_audio_to_storage(
        self, speaker_id: int, audio_bytes: bytes, audio_format: str
    ) -> str:
        """音声ファイルをストレージに保存."""
        file_path = f"voice_samples/{speaker_id}/{uuid4()}.{audio_format}"
        logger.info(f"Uploading to storage: {file_path}")

        storage_path = self.storage.upload(
            data=audio_bytes,
            path=file_path,
            content_type=f"audio/{audio_format}",
        )
        logger.info(f"Upload successful: {storage_path}")

        return storage_path

    def verify(
        self,
        speaker_id: str,
        audio_data: str,
        audio_format: str,
    ) -> AuthVerifyResult:
        """認証（1:1照合）.

        指定した話者との照合を行う。

        Args:
            speaker_id: 照合対象の話者ID
            audio_data: Base64エンコードされた音声データ
            audio_format: 音声フォーマット

        Returns:
            AuthVerifyResult: 認証結果

        Raises:
            NotFoundError: 話者が存在しない場合
        """
        logger.info(f"Verifying speaker: {speaker_id}")

        # 1. speaker_id から Speaker を取得
        speaker = self.speaker_repository.get_by_speaker_id(speaker_id)
        if speaker is None:
            raise NotFoundError("Speaker", speaker_id)
        assert speaker.id is not None

        # 2. 音声データをデコード
        audio_bytes = self._decode_audio_data(audio_data)

        # 3. 文字起こし（正規化済み）
        transcribed_text = self._transcribe_audio(audio_bytes, audio_format)
        logger.info(f"Transcribed text: {transcribed_text}")

        # 4. 登録済みパスフレーズを取得
        passphrases = self.passphrase_repository.get_by_speaker_id(speaker.id)
        if not passphrases:
            return AuthVerifyResult(
                authenticated=False,
                speaker_id=speaker_id,
                passphrase_match=False,
                voice_similarity=0.0,
                message="パスフレーズが登録されていません",
            )

        # 5. パスフレーズ照合（完全一致）
        registered_phrases = [p.phrase for p in passphrases]
        passphrase_match = transcribed_text in registered_phrases
        logger.info(f"Passphrase match: {passphrase_match}")

        # 6. 声紋比較（TODO: 未実装、スタブ値）
        voice_similarity = 0.85

        # 7. 認証判定
        # 現在はパスフレーズ一致のみで判定（声紋比較は未実装）
        authenticated = passphrase_match

        if authenticated:
            message = "認証成功"
        else:
            message = "認証失敗: パスフレーズが一致しません"

        return AuthVerifyResult(
            authenticated=authenticated,
            speaker_id=speaker_id,
            passphrase_match=passphrase_match,
            voice_similarity=voice_similarity,
            message=message,
        )

    def _transcribe_audio(self, audio_bytes: bytes, audio_format: str) -> str:
        """音声を文字起こし."""
        return self.worker_client.transcribe(audio_bytes, audio_format)

    def _extract_voiceprint(self, audio_bytes: bytes, audio_format: str) -> bytes:
        """声紋を抽出."""
        return self.worker_client.extract_voiceprint(audio_bytes, audio_format)
