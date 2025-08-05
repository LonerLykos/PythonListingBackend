from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import Listing
from app.models.car import Brand as BrandModel, CarModel
from app.models.region import Country as CountryModel, Region as RegionModel, City as CityModel
from app.schemas.listing import ListingCreate
from app.utils.profanity_filter import profanity_filter
from app.utils.storage import storage
from app.core.redis import redis_client as redis
from shared.utils.logging import setup_logging
from datetime import datetime, timezone

logger = setup_logging()


async def validate_references(
        db: AsyncSession,
        brand_id: int,
        car_model_id: int,
        country_id: int,
        region_id: int,
        city_id: int | None,
        # dealership_id: int | None
) -> None:
    if not await db.get(BrandModel, brand_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Brand does not exist")
    if not await db.get(CarModel, car_model_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model does not exist")
    if not await db.get(CountryModel, country_id):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Country does not exist")
    if not await db.get(RegionModel, region_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Region does not exist")
    if city_id and not await db.get(CityModel, city_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="City does not exist")
    # if dealership_id and not await db.get(DealershipModel, dealership_id):
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dealership does not exist")


async def check_profanity_attempts(redis_key: str, max_attempts: int = 2) -> bool:
    attempts = await redis.client.get(redis_key)
    attempts = int(attempts) if attempts else 0
    if attempts >= max_attempts:
        return False

    await redis.client.incr(redis_key)
    await redis.client.expire(redis_key, 24 * 60 * 60)
    return True


async def create_listing_service(
        db: AsyncSession,
        listing_data: ListingCreate,
        user_id: int,
        images: list[UploadFile]
) -> Listing:
    is_active = True
    redis_key = f"profanity_attempts:user:{user_id}"
    if not await profanity_filter(listing_data.description, listing_data.title, db):
        if not await check_profanity_attempts(redis_key):
            is_active = False
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profanity check failed")
    else:
        await redis.client.delete(redis_key)

    listing = Listing(
        user_id=listing_data.user_id,
        brand_id=listing_data.brand_id,
        car_model_id=listing_data.car_model_id,
        country_id=listing_data.country_id,
        region_id=listing_data.region_id,
        city_id=listing_data.city_id,
        original_price=listing_data.original_price,
        original_currency=listing_data.original_currency,
        price_uah=listing_data.price_uah,
        title=listing_data.title,
        description=listing_data.description,
        image_urls=listing_data.image_urls,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        dealership_id=listing_data.dealership_id
    )
    db.add(listing)
    await db.flush()

    if images:
        image_urls = await storage.save_images(listing.id, images)
        listing.image_urls = image_urls
        await db.merge(listing)

    await db.commit()
    await db.refresh(listing)
    return listing
