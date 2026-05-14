"""
Trend fetcher using Claude haiku + web_search tool.
Searches for trending Arabic Instagram cafe content.
"""
import json
import logging
from datetime import date
from typing import Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None

TREND_SYSTEM_PROMPT = """You are a social media trend analyst specializing in Arabic-language cafes and food culture on Instagram.
Your job is to identify what's currently trending on Arabic Instagram relevant to cafes, food, and lifestyle.
Always respond with a valid JSON object only, no markdown."""

TREND_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "trends": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_ar": {"type": "string"},
                    "topic_en": {"type": "string"},
                    "why_trending": {"type": "string"},
                    "hook_idea_ar": {"type": "string"},
                    "hook_idea_en": {"type": "string"},
                },
                "required": ["topic_ar", "topic_en", "why_trending", "hook_idea_ar", "hook_idea_en"],
            },
            "minItems": 3,
            "maxItems": 5,
        }
    },
    "required": ["trends"],
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def get_trends() -> list[dict]:
    """
    Uses Claude haiku with web_search to find current Arabic cafe Instagram trends.
    Returns a list of trend dicts with ar/en content.
    """
    client = _get_client()
    current_week = date.today().strftime("%Y-%m-%d")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            system=TREND_SYSTEM_PROMPT,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Search for the latest trending topics on Arabic Instagram for cafes and food as of {current_week}. "
                        "Search for 'ترندات انستجرام كافيه عربي' and 'trending Arabic cafe Instagram'. "
                        "Return a JSON object with a 'trends' array of 3-5 items, each with: "
                        "topic_ar, topic_en, why_trending, hook_idea_ar, hook_idea_en."
                    ),
                }
            ],
        )

        # Extract the final text block (after tool use)
        for block in reversed(response.content):
            if block.type == "text":
                text = block.text.strip()
                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                data = json.loads(text)
                trends = data.get("trends", [])
                logger.info("Fetched %d trends from web search", len(trends))
                return trends

    except Exception as exc:
        logger.warning("Trend fetching failed: %s — using fallback trends", exc)

    # Fallback static trends
    return [
        {
            "topic_ar": "لاتيه الكراميل",
            "topic_en": "Caramel Latte",
            "why_trending": "Popular autumn/winter beverage choice",
            "hook_idea_ar": "دفء الكراميل في كل رشفة ☕",
            "hook_idea_en": "Warmth in every sip",
        },
        {
            "topic_ar": "ديكور الكافيه",
            "topic_en": "Cafe Aesthetics",
            "why_trending": "Instagram reels of cozy cafe interiors are viral",
            "hook_idea_ar": "زاويتك المفضلة تنتظرك 📸",
            "hook_idea_en": "Your favorite corner is waiting",
        },
        {
            "topic_ar": "قهوة الصباح",
            "topic_en": "Morning Coffee Ritual",
            "why_trending": "Daily morning coffee content drives high engagement",
            "hook_idea_ar": "ابدأ يومك بالطريقة الصحيحة ☀️",
            "hook_idea_en": "Start your day right",
        },
    ]


def format_trends_for_prompt(trends: list[dict]) -> str:
    if not trends:
        return "No specific trends identified."
    lines = []
    for i, t in enumerate(trends, 1):
        lines.append(
            f"{i}. {t['topic_ar']} ({t['topic_en']})\n"
            f"   Why trending: {t['why_trending']}\n"
            f"   Hook idea (AR): {t['hook_idea_ar']}\n"
            f"   Hook idea (EN): {t['hook_idea_en']}"
        )
    return "\n".join(lines)
