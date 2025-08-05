import enum
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, Column, Integer, String, Boolean, DateTime, Float, Enum, Text
from sqlalchemy.dialects.mysql import JSON
from .base import Base


class Currency(enum.Enum):
    UAH = 'UAH'
    USD = 'USD'
    EUR = 'EUR'


class Listing(Base):
    __tablename__ = 'listings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=False)
    car_model_id = Column(Integer, ForeignKey('car_models.id'), nullable=False, index=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    region_id = Column(Integer, ForeignKey('regions_or_states.id'), nullable=False, index=True)
    city_id = Column(Integer, ForeignKey('cities.id'), nullable=True, index=True)
    original_price = Column(Float, nullable=False)
    original_currency = Column(Enum(Currency), nullable=False)
    price_uah = Column(Float, nullable=True, index=True)
    image_urls = Column(JSON, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    dealership_id = Column(Integer, nullable=True, default=None)
