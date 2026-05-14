from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event

router = APIRouter(prefix="/events")
templates = Jinja2Templates(directory="app/templates")

PROMO_TYPES = ["general", "discount", "new_item", "special", "seasonal"]


@router.get("", response_class=HTMLResponse)
def events_list(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).filter(Event.is_active == True).order_by(Event.created_at.desc()).all()
    return templates.TemplateResponse("events/form.html", {
        "request": request,
        "events": events,
        "promo_types": PROMO_TYPES,
    })


@router.post("")
def add_event(
    title_ar: str = Form(...),
    title_en: str = Form(""),
    description: str = Form(""),
    event_date: str = Form(""),
    promo_type: str = Form("general"),
    discount_percent: float = Form(0.0),
    db: Session = Depends(get_db),
):
    parsed_date = None
    if event_date:
        try:
            parsed_date = datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            pass

    event = Event(
        title_ar=title_ar,
        title_en=title_en,
        description=description,
        event_date=parsed_date,
        promo_type=promo_type,
        discount_percent=discount_percent,
        is_active=True,
    )
    db.add(event)
    db.commit()
    return RedirectResponse(url="/events", status_code=303)


@router.post("/{event_id}/delete")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_active = False
    db.commit()
    return RedirectResponse(url="/events", status_code=303)
