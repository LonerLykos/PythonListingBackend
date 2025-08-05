from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum


class Currency(str, Enum):
    UAH = "UAH"
    USD = "USD"
    EUR = "EUR"


class ListingBase(BaseModel):
    user_id: int
    brand_id: int
    car_model_id: int
    country_id: int
    region_id: int
    city_id: int | None
    original_price: float
    original_currency: Currency
    title: str
    description: str | None
    image_urls: list[str] | None
    dealership_id: int | None


class ListingCreate(ListingBase):
    price_uah: float | None


class Listing(ListingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingPremium(Listing):
    viewed: int | None
    viewed_by_today: int | None
    viewed_by_week: int | None
    viewed_by_month: int | None
    avg_price_country: float | None
    avg_price_region: float | None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
