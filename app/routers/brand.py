import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brand_voice import BrandVoice

router = APIRouter(prefix="/brand")
templates = Jinja2Templates(directory="app/templates")

COUNTRIES = ["UAE", "Saudi", "Qatar", "Kuwait", "Bahrain", "Oman", "Egypt", "Jordan", "Lebanon", "Other"]


@router.get("", response_class=HTMLResponse)
def brand_setup(request: Request, db: Session = Depends(get_db)):
    brand = db.query(BrandVoice).order_by(BrandVoice.updated_at.desc()).first()
    example_posts = []
    if brand and brand.example_posts:
        try:
            example_posts = json.loads(brand.example_posts)
        except Exception:
            example_posts = [brand.example_posts]
    return templates.TemplateResponse("brand/setup.html", {
        "request": request,
        "brand": brand,
        "example_posts": example_posts,
        "countries": COUNTRIES,
    })


@router.post("")
def save_brand(
    cafe_name: str = Form(...),
    personality_description: str = Form(""),
    target_audience: str = Form(""),
    tone_keywords: str = Form(""),
    language_preference: str = Form("ar_en"),
    instagram_handle: str = Form(""),
    country: str = Form(""),
    example1: str = Form(""),
    example2: str = Form(""),
    example3: str = Form(""),
    db: Session = Depends(get_db),
):
    examples = [e for e in [example1, example2, example3] if e.strip()]
    example_posts_json = json.dumps(examples, ensure_ascii=False)

    brand = db.query(BrandVoice).first()
    if brand:
        brand.cafe_name = cafe_name
        brand.personality_description = personality_description
        brand.target_audience = target_audience
        brand.tone_keywords = tone_keywords
        brand.language_preference = language_preference
        brand.instagram_handle = instagram_handle.lstrip("@")
        brand.country = country
        brand.example_posts = example_posts_json
    else:
        brand = BrandVoice(
            cafe_name=cafe_name,
            personality_description=personality_description,
            target_audience=target_audience,
            tone_keywords=tone_keywords,
            language_preference=language_preference,
            instagram_handle=instagram_handle.lstrip("@"),
            country=country,
            example_posts=example_posts_json,
        )
        db.add(brand)

    db.commit()
    return RedirectResponse(url="/brand?saved=1", status_code=303)
