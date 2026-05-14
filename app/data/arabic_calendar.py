"""
Arabic and Islamic occasions module.
Provides upcoming occasion detection for content generation.
Note: Islamic dates are approximate Gregorian equivalents and shift ~11 days earlier each year.
"""
from datetime import date, timedelta
from typing import Optional

# Static Gregorian-approximate occasions (non-Islamic)
FIXED_OCCASIONS = [
    {"month": 10, "day": 1,  "name_ar": "اليوم العالمي للقهوة", "name_en": "World Coffee Day",   "theme": "coffee"},
    {"month": 2,  "day": 14, "name_ar": "عيد الحب",             "name_en": "Valentine's Day",     "theme": "romantic"},
    {"month": 3,  "day": 21, "name_ar": "عيد الأم",             "name_en": "Mother's Day",         "theme": "family"},
    {"month": 1,  "day": 1,  "name_ar": "رأس السنة الميلادية",  "name_en": "New Year's Day",       "theme": "celebration"},
    {"month": 12, "day": 25, "name_ar": "عيد الميلاد",          "name_en": "Christmas",            "theme": "celebration"},
]

# National days (configurable — add/remove per target country)
NATIONAL_DAYS = {
    "UAE":   {"month": 12, "day": 2,  "name_ar": "اليوم الوطني الإماراتي",  "name_en": "UAE National Day"},
    "Saudi": {"month": 9,  "day": 23, "name_ar": "اليوم الوطني السعودي",    "name_en": "Saudi National Day"},
    "Qatar": {"month": 12, "day": 18, "name_ar": "اليوم الوطني القطري",     "name_en": "Qatar National Day"},
    "Kuwait":{"month": 2,  "day": 25, "name_ar": "اليوم الوطني الكويتي",   "name_en": "Kuwait National Day"},
    "Bahrain":{"month": 12,"day": 16, "name_ar": "اليوم الوطني البحريني",   "name_en": "Bahrain National Day"},
    "Oman":  {"month": 11, "day": 18, "name_ar": "اليوم الوطني العُماني",   "name_en": "Oman National Day"},
}

# Approximate Islamic dates for 2025-2026 (Gregorian).
# These must be updated annually as Islamic dates shift ~11 days per year.
ISLAMIC_OCCASIONS_2025_2026 = [
    {"date": date(2025, 3, 30),  "name_ar": "رمضان (بداية)",       "name_en": "Ramadan (Start)",      "theme": "ramadan_start"},
    {"date": date(2025, 3, 30),  "name_ar": "رمضان",               "name_en": "Ramadan",              "theme": "ramadan"},
    {"date": date(2025, 4, 20),  "name_ar": "ليلة القدر",          "name_en": "Laylat al-Qadr",       "theme": "spiritual"},
    {"date": date(2025, 4, 29),  "name_ar": "عيد الفطر",           "name_en": "Eid al-Fitr",          "theme": "eid_fitr"},
    {"date": date(2025, 6, 6),   "name_ar": "عيد الأضحى",         "name_en": "Eid al-Adha",          "theme": "eid_adha"},
    {"date": date(2025, 6, 27),  "name_ar": "رأس السنة الهجرية",  "name_en": "Islamic New Year",     "theme": "celebration"},
    {"date": date(2025, 9, 4),   "name_ar": "المولد النبوي",       "name_en": "Prophet's Birthday",   "theme": "spiritual"},
    # 2026 estimates
    {"date": date(2026, 3, 19),  "name_ar": "رمضان (بداية)",       "name_en": "Ramadan (Start)",      "theme": "ramadan_start"},
    {"date": date(2026, 4, 9),   "name_ar": "ليلة القدر",          "name_en": "Laylat al-Qadr",       "theme": "spiritual"},
    {"date": date(2026, 4, 18),  "name_ar": "عيد الفطر",           "name_en": "Eid al-Fitr",          "theme": "eid_fitr"},
    {"date": date(2026, 5, 27),  "name_ar": "عيد الأضحى",         "name_en": "Eid al-Adha",          "theme": "eid_adha"},
    {"date": date(2026, 6, 16),  "name_ar": "رأس السنة الهجرية",  "name_en": "Islamic New Year",     "theme": "celebration"},
    {"date": date(2026, 8, 25),  "name_ar": "المولد النبوي",       "name_en": "Prophet's Birthday",   "theme": "spiritual"},
]


def get_upcoming_occasions(days_ahead: int = 14, country: Optional[str] = None) -> list[dict]:
    """
    Returns occasions falling within [today, today + days_ahead].
    Each item: {name_ar, name_en, date, days_until, theme}
    """
    today = date.today()
    end = today + timedelta(days=days_ahead)
    results = []

    # Fixed occasions
    for occ in FIXED_OCCASIONS:
        occ_date = date(today.year, occ["month"], occ["day"])
        if occ_date < today:
            occ_date = date(today.year + 1, occ["month"], occ["day"])
        if today <= occ_date <= end:
            results.append({
                "name_ar": occ["name_ar"],
                "name_en": occ["name_en"],
                "date": occ_date.isoformat(),
                "days_until": (occ_date - today).days,
                "theme": occ.get("theme", "general"),
            })

    # National day
    if country and country in NATIONAL_DAYS:
        nd = NATIONAL_DAYS[country]
        nd_date = date(today.year, nd["month"], nd["day"])
        if nd_date < today:
            nd_date = date(today.year + 1, nd["month"], nd["day"])
        if today <= nd_date <= end:
            results.append({
                "name_ar": nd["name_ar"],
                "name_en": nd["name_en"],
                "date": nd_date.isoformat(),
                "days_until": (nd_date - today).days,
                "theme": "national_day",
            })

    # Islamic occasions
    for occ in ISLAMIC_OCCASIONS_2025_2026:
        occ_date = occ["date"]
        if today <= occ_date <= end:
            results.append({
                "name_ar": occ["name_ar"],
                "name_en": occ["name_en"],
                "date": occ_date.isoformat(),
                "days_until": (occ_date - today).days,
                "theme": occ.get("theme", "general"),
            })

    results.sort(key=lambda x: x["days_until"])
    return results


def format_occasions_for_prompt(occasions: list[dict]) -> str:
    if not occasions:
        return "No major occasions in the next 14 days."
    lines = []
    for occ in occasions:
        lines.append(
            f"- {occ['name_ar']} ({occ['name_en']}) — in {occ['days_until']} days [{occ['date']}]"
        )
    return "\n".join(lines)
