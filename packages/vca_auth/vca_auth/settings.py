from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """認証設定."""

    # 声紋類似度の閾値（0.0〜1.0）
    # この値以上の類似度で声紋一致と判定
    VOICE_SIMILARITY_THRESHOLD: float = 0.4

    model_config = {"env_prefix": "VCA_AUTH_"}


auth_settings = AuthSettings()
