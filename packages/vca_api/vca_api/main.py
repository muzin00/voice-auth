import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from vca_auth.exceptions import NotFoundError
from vca_engine import load_models

from vca_api.exception_handlers import not_found_exception_handler
from vca_api.routers.ws_enrollment import router as enrollment_router
from vca_api.routers.ws_identify import router as identify_router
from vca_api.routers.ws_verify import router as verify_router
from vca_api.routes.auth import router as auth_router
from vca_api.routes.demo import router as demo_router
from vca_api.settings import server_settings

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理."""
    # 起動時: モデルをプリロード
    load_models()
    yield
    # 終了時の処理（必要なら）


app = FastAPI(
    title="VCA Server",
    version="0.1.0",
    lifespan=lifespan,
)

# 例外ハンドラ登録
app.add_exception_handler(NotFoundError, not_found_exception_handler)

# 静的ファイルのマウント
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ルーター登録
app.include_router(auth_router)
app.include_router(demo_router)
app.include_router(enrollment_router)
app.include_router(verify_router)
app.include_router(identify_router)


@app.get("/")
def redirect_to_demo() -> RedirectResponse:
    """ルートパスからデモページへリダイレクト."""
    return RedirectResponse(url="/demo")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def run_server():
    uvicorn.run(
        "vca_api.main:app",
        host=server_settings.HOST,
        port=server_settings.PORT,
        workers=server_settings.WORKERS,
        reload=server_settings.HOT_RELOAD,
    )
