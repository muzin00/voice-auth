from fastapi import Request, status
from fastapi.responses import JSONResponse
from vca_auth.exceptions import NotFoundError


async def not_found_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """NotFoundErrorを404レスポンスに変換."""
    assert isinstance(exc, NotFoundError)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )
