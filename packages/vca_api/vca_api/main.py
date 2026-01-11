import uvicorn
from fastapi import FastAPI

from vca_api.routes.voices import router as voices_router
from vca_api.settings import server_settings

app = FastAPI(
    title="VCA Server",
    version="0.1.0",
)

app.include_router(voices_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def run_server():
    uvicorn.run(
        "vca_api.main:app",
        host=server_settings.HOST,
        port=server_settings.PORT,
        reload=server_settings.reload,
        workers=server_settings.workers,
    )
