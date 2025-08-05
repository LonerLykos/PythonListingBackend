from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.exchange_rate import ExchangeRate as ExchangeRateModel
from app.models.listing import Listing, Currency


async def create_price_uah(
        db: AsyncSession,
        original_price: float | None,
        original_currency: Currency | None,
        listing: Listing | None = None):
    today = date.today()
    exchange_rates: ExchangeRateModel = await db.scalar(select(ExchangeRateModel).where(
        ExchangeRateModel.created_at == today
    ))

    if listing and original_price and original_price == listing.original_price and original_currency and original_currency == listing.original_currency:
        return None

    if original_price is None and original_currency is None:
        return listing.price_uah

    if exchange_rates:
        if original_price and original_currency:
            if original_currency == Currency.UAH:
                return original_price
            elif original_currency == Currency.USD:
                return original_price * exchange_rates.sell_usd
            elif original_currency == Currency.EUR:
                return original_price * exchange_rates.sell_eur
        elif original_price:
            if listing.original_currency == Currency.UAH:
                return original_price
            elif listing.original_currency == Currency.USD:
                return original_price * exchange_rates.sell_usd
            elif listing.original_currency == Currency.EUR:
                return original_price * exchange_rates.sell_eur
        elif original_currency:
            if original_currency == Currency.UAH:
                return listing.original_price
            elif original_currency == Currency.USD:
                return listing.original_price * exchange_rates.sell_usd
            elif original_currency == Currency.EUR:
                return listing.original_price * exchange_rates.sell_eur

    return None
