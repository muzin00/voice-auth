from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

import pytest
from vca_infra.storages.gcs_storage import GCSStorage


class TestGCSStorage:
    """GCSStorageのユニットテスト"""

    @pytest.fixture
    def mock_storage_client(self) -> Generator[dict[str, Any], None, None]:
        """モックされたGCS Clientを作成."""
        with patch("vca_infra.storages.gcs_storage.storage") as mock_storage:
            mock_client = Mock()
            mock_bucket = Mock()
            mock_blob = Mock()

            mock_storage.Client.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            yield {
                "storage": mock_storage,
                "client": mock_client,
                "bucket": mock_bucket,
                "blob": mock_blob,
            }

    @pytest.fixture
    def storage(self, mock_storage_client: dict[str, Any]) -> GCSStorage:
        """GCSStorageインスタンスを作成."""
        return GCSStorage(bucket_name="test-bucket", project_id="test-project")

    def test_init(self, mock_storage_client: dict[str, Any]):
        """初期化が正しく行われる."""
        storage = GCSStorage(bucket_name="test-bucket", project_id="test-project")

        mock_storage_client["storage"].Client.assert_called_once_with(
            project="test-project"
        )
        mock_storage_client["client"].bucket.assert_called_once_with("test-bucket")
        assert storage.bucket_name == "test-bucket"

    def test_upload(self, storage: GCSStorage, mock_storage_client: dict[str, Any]):
        """ファイルのアップロードが成功する."""
        data = b"test audio data"
        path = "voices/1/test.wav"
        content_type = "audio/wav"

        result = storage.upload(data, path, content_type=content_type)

        # blob()が正しく呼ばれた
        mock_storage_client["bucket"].blob.assert_called_once_with(path)

        # upload_from_string()が正しく呼ばれた
        mock_storage_client["blob"].upload_from_string.assert_called_once_with(
            data, content_type=content_type
        )

        # gs://形式のパスが返される
        assert result == f"gs://test-bucket/{path}"

    def test_upload_without_content_type(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """content_type省略時もアップロードできる."""
        data = b"test data"
        path = "voices/1/test.mp3"

        result = storage.upload(data, path)

        mock_storage_client["blob"].upload_from_string.assert_called_once_with(
            data, content_type=None
        )
        assert result == "gs://test-bucket/voices/1/test.mp3"

    def test_delete_with_relative_path(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """相対パスでファイルを削除できる."""
        path = "voices/1/test.wav"

        storage.delete(path)

        # blob()が相対パスで呼ばれた
        mock_storage_client["bucket"].blob.assert_called_once_with(path)

        # delete()が呼ばれた
        mock_storage_client["blob"].delete.assert_called_once()

    def test_delete_with_gs_prefix(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """gs://プレフィックス付きパスを削除できる."""
        path = "gs://test-bucket/voices/1/test.wav"

        storage.delete(path)

        # gs://プレフィックスが除去される
        mock_storage_client["bucket"].blob.assert_called_once_with("voices/1/test.wav")
        mock_storage_client["blob"].delete.assert_called_once()

    def test_delete_handles_not_found(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """存在しないファイルの削除は例外を発生させない."""
        from google.cloud.exceptions import NotFound

        mock_storage_client["blob"].delete.side_effect = NotFound("File not found")

        # エラーが発生しないことを確認
        storage.delete("nonexistent/file.wav")

        mock_storage_client["blob"].delete.assert_called_once()

    def test_get_url_with_relative_path(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """相対パスで署名付きURLを取得できる."""
        path = "voices/1/test.wav"
        mock_storage_client[
            "blob"
        ].generate_signed_url.return_value = (
            "https://storage.googleapis.com/test-bucket/voices/1/test.wav?signature=..."
        )

        url = storage.get_url(path)

        # blob()が相対パスで呼ばれた
        mock_storage_client["bucket"].blob.assert_called_once_with(path)

        # generate_signed_url()がデフォルト引数で呼ばれた
        mock_storage_client["blob"].generate_signed_url.assert_called_once_with(
            version="v4", expiration=3600, method="GET"
        )

        assert url.startswith("https://storage.googleapis.com")

    def test_get_url_with_gs_prefix(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """gs://プレフィックス付きパスでURLを取得できる."""
        path = "gs://test-bucket/voices/1/test.wav"
        mock_storage_client[
            "blob"
        ].generate_signed_url.return_value = (
            "https://storage.googleapis.com/test-bucket/voices/1/test.wav?signature=..."
        )

        storage.get_url(path)

        # gs://プレフィックスが除去される
        mock_storage_client["bucket"].blob.assert_called_once_with("voices/1/test.wav")
        mock_storage_client["blob"].generate_signed_url.assert_called_once()

    def test_get_url_with_custom_expiration(
        self, storage: GCSStorage, mock_storage_client: dict[str, Any]
    ):
        """カスタム有効期限で署名付きURLを取得できる."""
        path = "voices/1/test.wav"
        expires_in = 7200
        mock_storage_client[
            "blob"
        ].generate_signed_url.return_value = (
            "https://storage.googleapis.com/test-bucket/voices/1/test.wav?signature=..."
        )

        storage.get_url(path, expires_in=expires_in)

        # generate_signed_url()がカスタム有効期限で呼ばれた
        mock_storage_client["blob"].generate_signed_url.assert_called_once_with(
            version="v4", expiration=expires_in, method="GET"
        )
