from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """サーバー起動設定"""

    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.ENVIRONMENT == "development"

    @property
    def reload(self) -> bool:
        """ホットリロードを有効にするか"""
        return self.is_development

    @property
    def workers(self) -> int:
        """ワーカー数（開発環境では1固定）"""
        return 1 if self.is_development else self.WORKERS


server_settings = ServerSettings()
