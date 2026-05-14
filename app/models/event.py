from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title_ar = Column(String(300), nullable=False)
    title_en = Column(String(300), default="")
    description = Column(Text, default="")
    event_date = Column(DateTime, nullable=True)
    promo_type = Column(String(50), default="general")  # discount/new_item/special/seasonal/general
    discount_percent = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
