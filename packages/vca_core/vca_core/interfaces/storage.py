from typing import Protocol


class StorageProtocol(Protocol):
    """ストレージインターフェース."""

    def upload(
        self,
        data: bytes,
        path: str,
        content_type: str | None = None,
    ) -> str:
        """
        ファイルをアップロードする.

        Args:
            data: ファイルデータ
            path: 保存先パス
            content_type: MIMEタイプ

        Returns:
            str: アップロードされたファイルのURL/パス
        """
        ...

    def delete(self, path: str) -> None:
        """ファイルを削除する."""
        ...

    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """署名付きURLを取得する."""
        ...
