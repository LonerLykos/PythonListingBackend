from datetime import date
from pydantic import BaseModel, ConfigDict


class ExchangeRate(BaseModel):
    id: int
    buy_usd: float
    sell_usd: float
    buy_eur: float
    sell_eur: float
    created_at: date

    model_config = ConfigDict(from_attributes=True)
