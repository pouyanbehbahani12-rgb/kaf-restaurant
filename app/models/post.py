from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class GeneratedPost(Base):
    __tablename__ = "generated_posts"

    id = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(String(20), nullable=False)   # ISO date string "2025-05-12"
    post_type = Column(String(20), nullable=False)         # caption/story_idea/promo/trend
    platform = Column(String(20), default="instagram")     # instagram/story
    content_ar = Column(Text, nullable=False)
    content_en = Column(Text, default="")
    hashtags_ar = Column(Text, default="[]")               # JSON array
    hashtags_en = Column(Text, default="[]")               # JSON array
    rationale = Column(Text, default="")
    status = Column(String(20), default="draft")           # draft/approved/rejected
    generation_metadata = Column(Text, default="{}")       # JSON: model, tokens, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
