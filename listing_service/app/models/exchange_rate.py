from datetime import date
from sqlalchemy import Column, Integer, Float, Date
from .base import Base


class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    id = Column(Integer, primary_key=True, index=True)
    buy_usd = Column(Float, nullable=False)
    sell_usd = Column(Float, nullable=False)
    buy_eur = Column(Float, nullable=False)
    sell_eur = Column(Float, nullable=False)
    created_at = Column(Date, default=date.today)
