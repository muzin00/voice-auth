"""Demo UI routes."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/demo/", response_class=HTMLResponse)
async def demo_page(request: Request) -> HTMLResponse:
    """Render the demo UI page."""
    return templates.TemplateResponse(
        "demo.html",
        {"request": request},
    )
