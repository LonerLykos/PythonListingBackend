from fastapi import Depends, status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.additional_request import (
    AddEntityRequest,
    AddCountry,
    AddRegion,
    AddCity,
    AddBrand,
    AddCarModel
)
from app.models.region import (
    Country as CountryModel,
    Region as RegionModel
)
from app.models.car import Brand as BrandModel
from app.services.admin_notification_event import creating_event


def normalize_name(name: str) -> str:
    return name.strip().lower()


async def additional_checker(user_id: int, request: AddEntityRequest, db: AsyncSession):
    if isinstance(request, AddCountry):
        country = await db.scalar(select(CountryModel).where(func.lower(CountryModel.name) == normalize_name(request.name)))
        if country:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Country already exists")
        await creating_event(request.type, request.name, None, None, None, None, user_id)
    elif isinstance(request, AddRegion):
        country_name_or_id = request.country_name
        country = await db.scalar(select(CountryModel)
                                  .options(selectinload(CountryModel.regions))
                                  .where(func.lower(CountryModel.name) == normalize_name(request.country_name)))
        if country:
            country_name_or_id = country.id
            if any(r.name.lower() == normalize_name(request.name) for r in country.regions):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Region already exists")
        await creating_event(request.type, country_name_or_id, request.name, None, None, None, user_id)
    elif isinstance(request, AddCity):
        country_name_or_id = request.country_name
        region_name_or_id = request.region_name
        country = await db.scalar(select(CountryModel)
                                  .options(selectinload(CountryModel.regions))
                                  .where(func.lower(CountryModel.name) == normalize_name(request.country_name)))
        if country:
            country_name_or_id = country.id
            region = next(
                (r for r in country.regions if normalize_name(r.name) == normalize_name(request.region_name)), None
            )
            if region:
                region_db = await db.scalar(select(RegionModel)
                                         .options(selectinload(RegionModel.cities))
                                         .where(RegionModel.id == region.id))
                region_name_or_id = region.id
                if any(c.name.lower() == normalize_name(request.name) for c in region_db.cities):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="City already exists")
        await creating_event(request.type, country_name_or_id, region_name_or_id, request.name, None, None, user_id)
    elif isinstance(request, AddBrand):
        brand = await db.scalar(select(BrandModel).where(func.lower(BrandModel.name) == normalize_name(request.name)))
        if brand:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand already exists")
        await creating_event(request.type, None, None, None, request.name, None, user_id)
    elif isinstance(request, AddCarModel):
        brand_name_or_id = request.brand_name
        brand = await db.scalar(select(BrandModel)
                                .options(selectinload(BrandModel.car_models))
                                .where(func.lower(BrandModel.name) == normalize_name(request.brand_name)))
        if brand:
            brand_name_or_id = brand.id
            if any(car.name.lower() == normalize_name(request.name) for car in brand.car_models):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Car_model already exists")
        await creating_event(request.type, None, None, None, brand_name_or_id, request.name, user_id)
    else:
        print('WRONG')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request type")
