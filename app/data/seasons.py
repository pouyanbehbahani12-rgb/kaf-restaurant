"""Season detection based on current month."""
from datetime import date


def get_current_season() -> dict:
    month = date.today().month

    if month in (12, 1, 2):
        return {"name_ar": "الشتاء", "name_en": "Winter",
                "theme": "warmth, hot drinks, cozy atmosphere, winter specials"}
    elif month in (3, 4, 5):
        return {"name_ar": "الربيع", "name_en": "Spring",
                "theme": "freshness, floral flavors, light drinks, outdoor seating"}
    elif month in (6, 7, 8):
        return {"name_ar": "الصيف", "name_en": "Summer",
                "theme": "cold drinks, ice cream, refreshing, beat the heat"}
    else:
        return {"name_ar": "الخريف", "name_en": "Autumn",
                "theme": "cozy vibes, warm spices, earthy tones, harvest flavors"}


def format_season_for_prompt(season: dict) -> str:
    return f"{season['name_ar']} ({season['name_en']}) — {season['theme']}"
