from sqlalchemy.ext.asyncio import AsyncSession
from listing_service.app.models.region import (
    Country as CountryModel,
    Region as RegionModel,
    City as CityModel
)
from listing_service.app.models.car import (
    Brand as BrandModel,
    CarModel
)


async def get_or_create_country(session: AsyncSession, name_or_id: str | int):
    if isinstance(name_or_id, int):
        country = await session.get(CountryModel, name_or_id)
        return country
    else:
        country = CountryModel(name=name_or_id)
        session.add(country)
        await session.flush()
        return country


async def get_or_create_region(session: AsyncSession, name_or_id: str | int, country_id: int):
    if isinstance(name_or_id, int):
        region = await session.get(RegionModel, name_or_id)
        return region
    else:
        region = RegionModel(name=name_or_id, country_id=country_id)
        session.add(region)
        await session.flush()
        return region


async def create_city(session: AsyncSession, name: str, region_id: int):
    city = CityModel(name=name, region_id=region_id)
    session.add(city)


async def get_or_create_brand(session: AsyncSession, name_or_id: str | int):
    if isinstance(name_or_id, int):
        brand = await session.get(BrandModel, name_or_id)
        return brand
    else:
        brand = BrandModel(name=name_or_id)
        session.add(brand)
        await session.flush()
        return brand


async def create_carmodel(session: AsyncSession, name: str, brand_id: int):
    city = CarModel(name=name, brand_id=brand_id)
    session.add(city)
