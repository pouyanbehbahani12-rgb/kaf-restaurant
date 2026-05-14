from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class BrandVoice(Base):
    __tablename__ = "brand_voice"

    id = Column(Integer, primary_key=True, index=True)
    cafe_name = Column(String(200), nullable=False)
    personality_description = Column(Text, default="")
    target_audience = Column(Text, default="")
    tone_keywords = Column(Text, default="")  # comma-separated
    language_preference = Column(String(10), default="ar_en")  # ar / ar_en
    example_posts = Column(Text, default="")  # JSON array of strings
    instagram_handle = Column(String(100), default="")
    country = Column(String(50), default="")  # for national day selection
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
