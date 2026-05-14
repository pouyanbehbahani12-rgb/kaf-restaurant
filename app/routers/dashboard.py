from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.data.arabic_calendar import get_upcoming_occasions
from app.models.brand_voice import BrandVoice
from app.models.post import GeneratedPost

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    brand = db.query(BrandVoice).order_by(BrandVoice.updated_at.desc()).first()

    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    all_posts = db.query(GeneratedPost).order_by(GeneratedPost.created_at.desc()).all()
    week_posts = [p for p in all_posts if p.week_start_date == week_start]

    stats = {
        "total": len(week_posts),
        "draft": sum(1 for p in week_posts if p.status == "draft"),
        "approved": sum(1 for p in week_posts if p.status == "approved"),
        "rejected": sum(1 for p in week_posts if p.status == "rejected"),
    }

    recent_posts = all_posts[:6]
    occasions = get_upcoming_occasions(days_ahead=14, country=brand.country if brand else None)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "brand": brand,
        "stats": stats,
        "recent_posts": recent_posts,
        "occasions": occasions,
        "week_start": week_start,
    })
