"""
Orchestrates the full weekly content generation pipeline.
Steps:
  1. Fetch brand + menu + events from DB
  2. Get Arabic calendar occasions
  3. Get current season
  4. Fetch trending topics via Claude web search
  5. Generate 8 posts via Claude Sonnet with prompt caching
  6. Save posts to DB as drafts
"""
import json
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data.arabic_calendar import get_upcoming_occasions
from app.data.seasons import get_current_season
from app.models.brand_voice import BrandVoice
from app.models.event import Event
from app.models.menu import MenuItem
from app.models.post import GeneratedPost
from app.services import claude_client, trend_fetcher

logger = logging.getLogger(__name__)

# Generator function for SSE progress streaming
def run_weekly_generation(db: Session):
    """
    Generator that yields progress strings and runs generation.
    Yields lines prefixed with "data: " for SSE compatibility.
    """
    yield "data: step:Fetching brand profile and menu...\n\n"

    brand = db.query(BrandVoice).order_by(BrandVoice.updated_at.desc()).first()
    if not brand:
        yield "data: error:No brand voice configured. Please set up your brand first.\n\n"
        return

    menu_items = db.query(MenuItem).filter(MenuItem.is_active == True).all()
    yield f"data: step:Loaded {len(menu_items)} menu items.\n\n"

    # Events: created in last 7 days OR with event_date in next 7 days
    today = date.today()
    week_ahead = today + timedelta(days=7)
    events = (
        db.query(Event)
        .filter(Event.is_active == True)
        .filter(
            (Event.event_date >= today) if True else True
        )
        .order_by(Event.created_at.desc())
        .limit(10)
        .all()
    )
    yield f"data: step:Found {len(events)} events this week.\n\n"

    yield "data: step:Checking upcoming Arabic occasions...\n\n"
    occasions = get_upcoming_occasions(days_ahead=14, country=brand.country or None)
    season = get_current_season()
    if occasions:
        occ_names = ", ".join(o["name_en"] for o in occasions)
        yield f"data: step:Occasions: {occ_names}.\n\n"
    else:
        yield "data: step:No major occasions in next 14 days.\n\n"

    yield "data: step:Searching for trending topics on Arabic Instagram...\n\n"
    trends = trend_fetcher.get_trends()
    yield f"data: step:Found {len(trends)} trending topics.\n\n"

    yield "data: step:Generating content with Claude Sonnet (this may take 30-60 seconds)...\n\n"
    try:
        result = claude_client.generate_weekly_content(
            brand=brand,
            menu_items=menu_items,
            events=events,
            occasions=occasions,
            season=season,
            trends=trends,
        )
    except Exception as exc:
        logger.error("Content generation failed: %s", exc)
        yield f"data: error:Content generation failed: {exc}\n\n"
        return

    posts_data = result["result"].get("posts", [])
    week_theme = result["result"].get("week_theme", "")
    metadata = result["metadata"]
    week_start = today.strftime("%Y-%m-%d")

    yield f"data: step:Saving {len(posts_data)} posts to database...\n\n"

    saved = 0
    for post_dict in posts_data:
        post = GeneratedPost(
            week_start_date=week_start,
            post_type=post_dict.get("post_type", "caption"),
            platform=post_dict.get("platform", "instagram"),
            content_ar=post_dict.get("content_ar", ""),
            content_en=post_dict.get("content_en", ""),
            hashtags_ar=json.dumps(post_dict.get("hashtags_ar", []), ensure_ascii=False),
            hashtags_en=json.dumps(post_dict.get("hashtags_en", []), ensure_ascii=False),
            rationale=post_dict.get("rationale", ""),
            status="draft",
            generation_metadata=json.dumps({
                **metadata,
                "week_theme": week_theme,
                "occasions": [o["name_en"] for o in occasions],
                "season": season["name_en"],
            }),
        )
        db.add(post)
        saved += 1

    db.commit()

    cache_read = metadata.get("cache_read_tokens", 0)
    cache_info = f" (cache hit: {cache_read} tokens)" if cache_read > 0 else " (cache miss — first run)"
    yield f"data: done:{saved} posts generated successfully{cache_info}. Week theme: {week_theme}\n\n"
