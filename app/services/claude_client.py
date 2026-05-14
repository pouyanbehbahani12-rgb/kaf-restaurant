"""
Anthropic Claude SDK client with prompt caching.
Two cache breakpoints:
  1. Brand voice block  (cache_control ttl=1h)  — changes rarely
  2. Menu items block   (cache_control ephemeral) — changes when menu updated
Volatile context (events, occasions, season, trends) goes in the USER message only.
"""
import json
import logging
from datetime import date
from typing import Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None

# ── Static base instructions (never interpolated, counts toward cache token min) ──
BASE_INSTRUCTIONS = """You are an expert social media content strategist for Arabic-speaking cafes and restaurants.
Your role is to create authentic, engaging, and culturally relevant Instagram content in Arabic and English
that perfectly matches the cafe's brand voice, resonates with its audience, and drives engagement.

CONTENT GUIDELINES:
- Always write Arabic content first (RTL). Arabic should feel natural and conversational, not translated.
- English translations should be localized, not literal word-for-word translations.
- Understand Arabic culture, Islamic occasions, Gulf and Levant social norms.
- Hashtags: include a mix of Arabic (#كافيه #قهوة) and English (#cafe #coffee) hashtags.
- Emojis are welcome — they perform well on Arabic Instagram.
- Captions: 2-4 sentences, conversational, end with a question or call-to-action.
- Story ideas: describe the concept clearly so the manager can execute it.
- Promo posts: lead with the offer, make it exciting, add urgency if appropriate.
- Trend posts: ride the trend authentically — don't force it.

POST TYPE DEFINITIONS:
- caption: A polished Instagram feed post caption (2-4 sentences + hashtags)
- story_idea: A description of an Instagram Story concept (what to show, text overlay, interactive element)
- promo: A promotional post highlighting a discount, new item, or special event
- trend: A post that taps into a current trending topic or viral format

OUTPUT FORMAT:
You MUST return a valid JSON object matching this exact schema:
{
  "posts": [
    {
      "post_type": "caption | story_idea | promo | trend",
      "platform": "instagram | story",
      "content_ar": "Arabic text...",
      "content_en": "English text...",
      "hashtags_ar": ["#كافيه", ...],
      "hashtags_en": ["#cafe", ...],
      "rationale": "Brief explanation of why this post works"
    }
  ],
  "week_theme": "Overall theme for the week",
  "trend_insights": "Brief note on the trends used"
}

Generate exactly 8 posts per week: 3 captions, 2 story ideas, 2 promo posts, 1 trend post.
All posts must be ready to use — no placeholders."""

WEEKLY_CONTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "post_type": {"type": "string", "enum": ["caption", "story_idea", "promo", "trend"]},
                    "platform": {"type": "string", "enum": ["instagram", "story"]},
                    "content_ar": {"type": "string"},
                    "content_en": {"type": "string"},
                    "hashtags_ar": {"type": "array", "items": {"type": "string"}},
                    "hashtags_en": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": ["post_type", "platform", "content_ar", "content_en", "hashtags_ar", "hashtags_en", "rationale"],
                "additionalProperties": False,
            },
            "minItems": 8,
            "maxItems": 8,
        },
        "week_theme": {"type": "string"},
        "trend_insights": {"type": "string"},
    },
    "required": ["posts", "week_theme", "trend_insights"],
    "additionalProperties": False,
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _build_system_blocks(brand, menu_items: list) -> list[dict]:
    """
    Builds the cached system prompt.
    Block 1: Static base instructions (no cache marker — contributes to prefix size)
    Block 2: Brand voice (cache_control ttl=1h — changes rarely)
    Block 3: Menu items (cache_control ephemeral — cache on top of brand)
    """
    base_block = {
        "type": "text",
        "text": BASE_INSTRUCTIONS,
    }

    tone_keywords = brand.tone_keywords or ""
    example_posts = ""
    try:
        posts_list = json.loads(brand.example_posts or "[]")
        if posts_list:
            example_posts = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(posts_list))
    except Exception:
        example_posts = brand.example_posts or ""

    brand_block = {
        "type": "text",
        "text": (
            f"CAFE IDENTITY:\n"
            f"Name: {brand.cafe_name}\n"
            f"Country/Region: {brand.country or 'Gulf region'}\n"
            f"Instagram: @{brand.instagram_handle or 'cafe'}\n"
            f"Personality: {brand.personality_description}\n"
            f"Target Audience: {brand.target_audience}\n"
            f"Tone Keywords: {tone_keywords}\n"
            f"Language Preference: {brand.language_preference}\n\n"
            f"EXAMPLE POSTS IN OUR VOICE:\n{example_posts or '(No examples provided yet)'}"
        ),
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    }

    menu_lines = []
    for item in menu_items:
        if item.is_active:
            name = f"{item.name_ar}" + (f" / {item.name_en}" if item.name_en else "")
            desc = item.description_ar or item.description_en or ""
            price_str = f" — {item.price}" if item.price else ""
            cat_str = f" [{item.category}]" if item.category else ""
            menu_lines.append(f"- {name}{cat_str}: {desc}{price_str}")

    menu_text = "\n".join(menu_lines) if menu_lines else "(No menu items added yet)"
    menu_block = {
        "type": "text",
        "text": f"MENU ITEMS:\n{menu_text}",
        "cache_control": {"type": "ephemeral"},
    }

    return [base_block, brand_block, menu_block]


def _build_volatile_user_message(events: list, occasions: list, season: dict, trends: list) -> str:
    """
    Builds the volatile user message with current-week context.
    NEVER put time-sensitive data in the system prompt.
    """
    today = date.today()
    week_start = today.strftime("%Y-%m-%d")

    # Events
    if events:
        event_lines = []
        for e in events:
            title = e.title_ar + (f" / {e.title_en}" if e.title_en else "")
            promo = f" ({e.promo_type}" + (f", {int(e.discount_percent)}% off)" if e.discount_percent else ")")
            event_lines.append(f"- {title}{promo}: {e.description or ''}")
        events_str = "\n".join(event_lines)
    else:
        events_str = "No specific events this week."

    # Occasions
    if occasions:
        occ_lines = [
            f"- {occ['name_ar']} ({occ['name_en']}) in {occ['days_until']} days"
            for occ in occasions
        ]
        occasions_str = "\n".join(occ_lines)
    else:
        occasions_str = "No major occasions in the next 14 days."

    # Season
    season_str = f"{season['name_ar']} ({season['name_en']}) — {season['theme']}"

    # Trends
    if trends:
        trend_lines = [
            f"{i+1}. {t['topic_ar']} ({t['topic_en']}): {t['why_trending']} | Hook: {t['hook_idea_ar']}"
            for i, t in enumerate(trends)
        ]
        trends_str = "\n".join(trend_lines)
    else:
        trends_str = "No specific trends this week."

    return (
        f"Generate this week's social media content.\n\n"
        f"WEEK OF: {week_start}\n"
        f"CURRENT SEASON: {season_str}\n\n"
        f"UPCOMING OCCASIONS (next 14 days):\n{occasions_str}\n\n"
        f"THIS WEEK'S EVENTS & PROMOTIONS:\n{events_str}\n\n"
        f"TRENDING NOW:\n{trends_str}\n\n"
        f"Generate exactly 8 posts (3 captions, 2 story ideas, 2 promos, 1 trend post). "
        f"Return valid JSON only, no markdown."
    )


def generate_weekly_content(brand, menu_items: list, events: list, occasions: list, season: dict, trends: list) -> dict:
    """
    Main generation call using claude-sonnet-4-6 with prompt caching.
    Returns parsed dict with 'posts', 'week_theme', 'trend_insights'.
    """
    client = _get_client()
    system_blocks = _build_system_blocks(brand, menu_items)
    user_message = _build_volatile_user_message(events, occasions, season, trends)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_blocks,
        messages=[{"role": "user", "content": user_message}],
    )

    # Log cache metrics
    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_write = getattr(usage, "cache_creation_input_tokens", 0)
    logger.info(
        "Generation complete | input=%d cache_write=%d cache_read=%d output=%d",
        usage.input_tokens,
        cache_write,
        cache_read,
        usage.output_tokens,
    )

    # Extract text block
    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text.strip()
            break

    if not text:
        raise ValueError("Claude returned no text content")

    # Strip markdown fences if present
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    data = json.loads(text)

    metadata = {
        "model": "claude-sonnet-4-6",
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
    }

    return {"result": data, "metadata": metadata}
