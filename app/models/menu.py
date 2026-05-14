from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name_ar = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=False, default="")
    description_ar = Column(Text, default="")
    description_en = Column(Text, default="")
    price = Column(Float, nullable=False, default=0.0)
    category = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
