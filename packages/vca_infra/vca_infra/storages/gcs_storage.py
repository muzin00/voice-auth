from typing import Any

from google.cloud import storage  # type: ignore[import-untyped]
from google.cloud.exceptions import NotFound


class GCSStorage:
    """Google Cloud Storage実装."""

    client: Any
    bucket: Any

    def __init__(self, bucket_name: str, project_id: str | None = None) -> None:
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name

    def upload(
        self,
        data: bytes,
        path: str,
        content_type: str | None = None,
    ) -> str:
        """ファイルをGCSにアップロード."""
        blob = self.bucket.blob(path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket_name}/{path}"

    def delete(self, path: str) -> None:
        """ファイルを削除."""
        if path.startswith("gs://"):
            path = path.replace(f"gs://{self.bucket_name}/", "")

        blob = self.bucket.blob(path)
        try:
            blob.delete()
        except NotFound:
            pass

    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """署名付きURLを取得."""
        if path.startswith("gs://"):
            path = path.replace(f"gs://{self.bucket_name}/", "")

        blob = self.bucket.blob(path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=expires_in,
            method="GET",
        )
        return url
