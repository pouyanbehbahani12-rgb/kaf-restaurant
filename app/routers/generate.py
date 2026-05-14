import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.services.content_generator import run_weekly_generation

router = APIRouter(prefix="/generate")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def generate_page(request: Request):
    return templates.TemplateResponse("generate/progress.html", {"request": request})


@router.post("")
def trigger_generation():
    """Redirect to SSE progress page after POST."""
    return RedirectResponse(url="/generate/stream", status_code=303)


@router.get("/stream")
def generation_stream(request: Request):
    """
    SSE endpoint: streams progress messages from content_generator.
    Each message is a 'data: ...' line for EventSource.
    """
    def event_generator():
        db = SessionLocal()
        try:
            for message in run_weekly_generation(db):
                yield message
        except Exception as exc:
            yield f"data: error:{exc}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
