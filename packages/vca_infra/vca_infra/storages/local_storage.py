from pathlib import Path


class LocalStorage:
    """ローカルファイルシステム実装（開発環境用）."""

    def __init__(self, base_path: str = "/tmp") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        data: bytes,
        path: str,
        content_type: str | None = None,
    ) -> str:
        """ファイルをローカルに保存."""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)

        return str(file_path)

    def delete(self, path: str) -> None:
        """ファイルを削除."""
        file_path = Path(path) if path.startswith("/") else self.base_path / path
        if file_path.exists():
            file_path.unlink()

    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """ローカルパスを返す."""
        return path
