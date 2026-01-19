from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """サーバー起動設定"""

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1  # ワーカー数（AIモデルを扱う場合、Cloud Runでは1固定が推奨）
    HOT_RELOAD: bool = False


server_settings = ServerSettings()
