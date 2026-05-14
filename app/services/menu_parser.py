"""
Menu file parser: supports PDF and JSON uploads.
PDF: pdfplumber extracts text, Claude haiku structures it.
JSON: direct parse with flexible schema support.
"""
import json
import logging
import io
from typing import Optional

import anthropic
import pdfplumber

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None

EXTRACTION_PROMPT = """Extract all menu items from the following text and return a JSON array.
Each item must have: name_ar (Arabic name), name_en (English name, empty string if not present),
description_ar (Arabic description), description_en (English description),
price (number, 0 if not found), category (e.g. "Coffee", "Food", "Dessert", "Juice").
Return ONLY a valid JSON array, no markdown."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def parse_pdf(file_bytes: bytes) -> list[dict]:
    """Extract text from PDF then use Claude to structure menu items."""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    if not text.strip():
        logger.warning("PDF text extraction returned empty content")
        return []

    client = _get_client()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": f"Menu text:\n\n{text}"}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    items = json.loads(raw)
    logger.info("Parsed %d menu items from PDF", len(items))
    return items


def parse_json(file_bytes: bytes) -> list[dict]:
    """
    Parse JSON menu file. Supports two formats:
    1. Array: [{name_ar, name_en, price, category, ...}, ...]
    2. Nested: {categories: {name: [items]}}
    """
    data = json.loads(file_bytes.decode("utf-8"))

    if isinstance(data, list):
        return _normalize_items(data)

    # Nested format
    if isinstance(data, dict):
        items = []
        categories = data.get("categories", data)
        if isinstance(categories, dict):
            for cat_name, cat_items in categories.items():
                if isinstance(cat_items, list):
                    for item in cat_items:
                        item.setdefault("category", cat_name)
                        items.append(item)
            return _normalize_items(items)
        # Try "items" key
        if "items" in data:
            return _normalize_items(data["items"])

    raise ValueError("Unrecognized JSON menu format")


def _normalize_items(items: list) -> list[dict]:
    normalized = []
    for item in items:
        normalized.append({
            "name_ar": item.get("name_ar") or item.get("name") or "",
            "name_en": item.get("name_en") or item.get("name_english") or "",
            "description_ar": item.get("description_ar") or item.get("description") or "",
            "description_en": item.get("description_en") or "",
            "price": float(item.get("price", 0) or 0),
            "category": item.get("category") or item.get("type") or "",
        })
    return normalized
