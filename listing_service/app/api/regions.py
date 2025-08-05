from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.schemas.region import (
    CountryBase,
    Country as CountryResponse,
    RegionBase,
    Region as RegionResponse,
    CityBase,
    City as CityResponse,
    RegionInCountry,
    CitiesInRegion, CountryWithRegions, RegionWithCities
)
from app.schemas.listing import MessageResponse
from app.models.user import User
from app.models.region import Country as CountryModel, Region as RegionModel, City as CityModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/location", tags=["location"])


@router.get('/countries', response_model=list[CountryResponse], status_code=status.HTTP_200_OK)
async def get_all_countries(
        db: AsyncSession = Depends(get_listing_db)):
    db_countries = await db.execute(select(CountryModel))
    return db_countries.scalars().all()


@router.post('/countries', response_model=CountryResponse, status_code=status.HTTP_201_CREATED)
async def create_country(
        country: CountryBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    country_check = await db.execute(select(CountryModel).where(CountryModel.name == country.name))
    if country_check.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Country already exists')
    db_country = CountryModel(name=country.name)
    db.add(db_country)
    await db.commit()
    await db.refresh(db_country)
    return db_country


@router.delete('/countries/{country_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_country(
        country_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    db_country = await db.get(CountryModel, country_id)
    if not db_country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Country not found')
    await db.delete(db_country)
    await db.commit()
    return MessageResponse(message=f'Country {country_id} deleted')


@router.get('/country-with-regions/{country_id}', response_model=CountryWithRegions, status_code=status.HTTP_200_OK)
async def get_country_with_regions(
        country_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    country_with_regions = await db.scalar(
        select(CountryModel)
        .options(selectinload(CountryModel.regions))
        .where(CountryModel.id == country_id)
    )
    if not country_with_regions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Country not found')
    return country_with_regions


@router.get('/regions', response_model=list[RegionResponse], status_code=status.HTTP_200_OK)
async def get_all_regions(
        db: AsyncSession = Depends(get_listing_db)):
    db_regions = await db.execute(select(RegionModel))
    return db_regions.scalars().all()


@router.post('/regions', response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
async def create_region(
        region: RegionBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    country_with_regions: CountryWithRegions | None = await db.scalar(
        select(CountryModel)
        .options(selectinload(CountryModel.regions))
        .where(CountryModel.id == region.country_id)
    )
    if not country_with_regions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Country not found')

    if any(r.name == region.name for r in country_with_regions.regions):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Region already exists')

    db_region = RegionModel(
        name=region.name,
        country_id=region.country_id,
    )
    db.add(db_region)
    await db.commit()
    await db.refresh(db_region)
    return db_region


@router.delete('/regions/{region_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_region(
        region_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    db_region = await db.get(RegionModel, region_id)
    if not db_region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Region not found')
    await db.delete(db_region)
    await db.commit()
    return MessageResponse(message=f'Region {region_id} deleted')


@router.get('/region-with-cities/{region_id}', response_model=RegionWithCities, status_code=status.HTTP_200_OK)
async def get_region_with_cities(
        region_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    region_with_cities = await db.scalar(
        select(RegionModel)
        .options(selectinload(RegionModel.cities))
        .where(RegionModel.id == region_id)
    )
    if not region_with_cities:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Region not found')
    return region_with_cities


@router.get('/cities', response_model=list[CityResponse], status_code=status.HTTP_200_OK)
async def get_all_cities(
        db: AsyncSession = Depends(get_listing_db)):
    db_cities = await db.execute(select(CityModel))
    return db_cities.scalars().all()


@router.post('/cities', response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
        city: CityBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    region_check = await db.get(RegionModel, city.region_id)
    if not region_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Region not found')
    db_city = CityModel(
        name=city.name,
        region_id=city.region_id,
    )
    db.add(db_city)
    await db.commit()
    await db.refresh(db_city)
    return db_city


@router.delete('/cities/{city_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_city(
        city_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_regions')
    db_city = await db.get(CityModel, city_id)
    if not db_city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='City not found')
    await db.delete(db_city)
    await db.commit()
    return MessageResponse(message=f'City {city_id} deleted')


@router.get('/regions-by-country/{country_id}', response_model=list[RegionInCountry], status_code=status.HTTP_200_OK)
async def get_regions_by_country(
        country_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    country = await db.scalar(select(CountryModel).options(selectinload(CountryModel.regions)).where(CountryModel.id == country_id))
    if not country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Country not found')
    return country.regions


@router.get('/cities-by-region/{region_id}', response_model=list[CitiesInRegion], status_code=status.HTTP_200_OK)
async def get_cities_by_region(
        region_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    region = await db.scalar(select(RegionModel).options(selectinload(RegionModel.cities)).where(RegionModel.id == region_id))
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Region not found')
    return region.cities
