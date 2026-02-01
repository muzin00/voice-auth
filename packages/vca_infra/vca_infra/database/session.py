from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlmodel import Session, create_engine

from vca_infra.settings import db_settings

engine = create_engine(
    db_settings.database_url,
    echo=db_settings.ECHO,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """SQLite接続時に安全な設定を適用.

    GCSマウント環境でのSQLite運用に対応するため、
    ファイルロックに依存しない設定を適用する。
    """
    if db_settings.DB_TYPE == "sqlite":
        cursor = dbapi_connection.cursor()
        # WALモードは複数ファイルを使うためGCS FUSEと相性が悪い
        cursor.execute("PRAGMA journal_mode=DELETE")
        # ロック待機時間を30秒に設定
        cursor.execute("PRAGMA busy_timeout=30000")
        # 安全な同期モード
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """コンテキストマネージャとしてセッションを取得.

    WebSocketハンドラなど、FastAPIの依存性注入が使えない場所で使用。
    """
    with Session(engine) as session:
        yield session
