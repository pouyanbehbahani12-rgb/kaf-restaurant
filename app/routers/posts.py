import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.post import GeneratedPost

router = APIRouter(prefix="/posts")
templates = Jinja2Templates(directory="app/templates")


def _post_to_dict(post: GeneratedPost) -> dict:
    try:
        hashtags_ar = json.loads(post.hashtags_ar or "[]")
    except Exception:
        hashtags_ar = []
    try:
        hashtags_en = json.loads(post.hashtags_en or "[]")
    except Exception:
        hashtags_en = []
    return {
        "id": post.id,
        "week_start_date": post.week_start_date,
        "post_type": post.post_type,
        "platform": post.platform,
        "content_ar": post.content_ar,
        "content_en": post.content_en,
        "hashtags_ar": hashtags_ar,
        "hashtags_en": hashtags_en,
        "rationale": post.rationale,
        "status": post.status,
        "created_at": post.created_at,
        "approved_at": post.approved_at,
    }


@router.get("", response_class=HTMLResponse)
def list_posts(
    request: Request,
    status: str = "all",
    week: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(GeneratedPost)
    if status != "all":
        query = query.filter(GeneratedPost.status == status)
    if week:
        query = query.filter(GeneratedPost.week_start_date == week)
    posts = query.order_by(GeneratedPost.created_at.desc()).all()

    # Available weeks for filter
    all_weeks = sorted(
        {p.week_start_date for p in db.query(GeneratedPost).all()},
        reverse=True,
    )

    return templates.TemplateResponse(request, "posts/list.html", context={
        "posts": [_post_to_dict(p) for p in posts],
        "current_status": status,
        "current_week": week,
        "all_weeks": all_weeks,
    })


@router.get("/{post_id}", response_class=HTMLResponse)
def post_detail(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(request, "posts/detail.html", context={
        "post": _post_to_dict(post),
    })


@router.post("/{post_id}/approve")
def approve_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = "approved"
    post.approved_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.post("/{post_id}/reject")
def reject_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = "rejected"
    db.commit()
    return RedirectResponse(url="/posts", status_code=303)


@router.post("/{post_id}/edit")
def edit_post(
    post_id: int,
    content_ar: str = Form(...),
    content_en: str = Form(""),
    hashtags_ar: str = Form(""),
    hashtags_en: str = Form(""),
    db: Session = Depends(get_db),
):
    post = db.query(GeneratedPost).filter(GeneratedPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.content_ar = content_ar
    post.content_en = content_en

    # Parse hashtags from comma-separated or space-separated strings
    def parse_tags(raw: str) -> list:
        tags = [t.strip().lstrip("#") for t in raw.replace(",", " ").split() if t.strip()]
        return [f"#{t}" for t in tags]

    post.hashtags_ar = json.dumps(parse_tags(hashtags_ar), ensure_ascii=False)
    post.hashtags_en = json.dumps(parse_tags(hashtags_en), ensure_ascii=False)
    db.commit()
    return RedirectResponse(url=f"/posts/{post_id}", status_code=303)


@router.get("/export/json")
def export_posts(week: str = "", db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse

    query = db.query(GeneratedPost).filter(GeneratedPost.status == "approved")
    if week:
        query = query.filter(GeneratedPost.week_start_date == week)
    posts = query.all()
    return JSONResponse([_post_to_dict(p) for p in posts])
