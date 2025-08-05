from pydantic import BaseModel
from datetime import datetime


class BotTaskData(BaseModel):
    title: str
    country_name_or_id: str | int | None = None
    region_name_or_id: str | int | None = None
    city_name: str | None = None
    brand_name_or_id: str | int | None= None
    car_model_name: str | None = None
    who_ask_for: int
    created_at: datetime = datetime.now()
