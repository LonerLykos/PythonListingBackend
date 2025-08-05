from datetime import date, timedelta
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form,
    File,
    UploadFile
)
from sqlalchemy import select, func, delete
from app.core.redis import redis_client as redis
from app.models.statistic_for_premium import ListingView
from app.schemas.listing import (
    ListingCreate,
    Listing as ListingResponse,
    ListingPremium as ListingPremiumResponse,
    MessageResponse,
)
from app.schemas.additional_request import (
    AddEntityRequest,
    AddCountry,
    AddRegion,
    AddCity,
    AddBrand,
    AddCarModel
)
from app.models.statistic_for_premium import ListingView as ListingViewModel
from app.models.listing import Listing as ListingModel, Currency
from app.models.user import User
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.listing import validate_references, create_listing_service, check_profanity_attempts
from app.services.permissions_checker import permission_checker
from app.services.admin_notification_event import notification_event, creating_event
from app.utils.additional_checker import additional_checker
from app.utils.create_price_uah import create_price_uah
from app.utils.profanity_filter import profanity_filter
from app.utils.token_utils import get_user_from_token, get_optional_user_from_token
from app.utils.storage import storage
from app.models.region import (
    Country as CountryModel,
    Region as RegionModel,
    City as CityModel
)
from app.models.car import Brand as BrandModel, CarModel
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[ListingResponse], status_code=status.HTTP_200_OK)
async def get_all_active_listings(db: AsyncSession = Depends(get_listing_db)):
    result = await db.execute(select(ListingModel).filter(ListingModel.is_active == True))
    listings = result.scalars().all()
    return listings


@router.post("", response_model=ListingResponse | MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db),
        brand_id: int = Form(...),
        car_model_id: int = Form(...),
        country_id: int = Form(...),
        region_id: int = Form(...),
        city_id: int | None = Form(None),
        original_price: float = Form(...),
        original_currency: Currency = Form(...),
        title: str = Form(...),
        description: str | None = Form(None),
        images: list[UploadFile] = File(default_factory=list),
        dealership_id: int | None = Form(None)
):
    await permission_checker(user, 'manage_listings')
    listings_result = await db.execute(select(ListingModel).filter(ListingModel.user_id == user.id))
    listings =  listings_result.scalars().all()
    if  user.role.name != 'admin':
        if not user.is_premium and len(listings) >= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You need to be a premium user for creating more than 1 listing"
            )

    await validate_references(db, brand_id, car_model_id, country_id, region_id, city_id)

    if images and len(images) > 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 3 images allowed")

    allowed_extensions = {".jpg", ".jpeg", ".png"}
    for file in images:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file format: {file.filename}")

    price_uah = await create_price_uah(db, original_price, original_currency)

    listing_data = ListingCreate(
        user_id=user.id,
        brand_id=brand_id,
        car_model_id=car_model_id,
        country_id=country_id,
        region_id=region_id,
        city_id=city_id,
        original_price=original_price,
        original_currency=original_currency,
        price_uah=price_uah,
        title=title,
        description=description,
        image_urls=[],
        dealership_id=dealership_id
    )

    listing: ListingResponse = await create_listing_service(db, listing_data, user.id, images)

    if not listing.is_active:
        await notification_event(listing)
        return MessageResponse(message="Your listing is under moderation")

    return listing


@router.get('/all_listings', response_model=list[ListingResponse], status_code=status.HTTP_200_OK)
async def get_all_listings(
        user: User= Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'moderate_listings')
    result = await db.execute(select(ListingModel))
    listings = result.scalars().all()
    return listings


@router.get('/moderating_listings', response_model=list[ListingResponse], status_code=status.HTTP_200_OK)
async def get_moderating_listings(
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'moderate_listings')
    inactive_listings = await db.execute(select(ListingModel).filter(ListingModel.is_active == False))
    return inactive_listings.scalars().all()


@router.post('/additional-request', response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_sub_info(
        request: AddEntityRequest,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await additional_checker(user.id, request, db)
    return MessageResponse(message=f"Successfully created request for adding new {request.type}")


@router.patch('/{current_listing_id}', response_model=ListingResponse, status_code=status.HTTP_200_OK)
async def toggle_listing_status(
        current_listing_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    listing = await db.get(ListingModel, current_listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    is_moderator = any(p.name == 'moderate_listings' for p in user.role.permissions)
    if listing.user_id != user.id and not is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't manage this listing")
    listing.is_active = not listing.is_active
    await db.commit()
    await db.refresh(listing)
    return listing


@router.get("/{current_listing_id}", response_model=ListingResponse | ListingPremiumResponse, status_code=status.HTTP_200_OK)
async def get_active_listing_by_id(
        current_listing_id: int,
        user: User | None = Depends(get_optional_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    """Get a listing."""
    listing_base: ListingModel | None = await db.get(ListingModel, current_listing_id)
    is_moderator = None
    if user:
        is_moderator = any(p.name == 'moderate_listings' for p in user.role.permissions)
    if not listing_base or (not listing_base.is_active and not is_moderator):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if not user or user.id != listing_base.user_id:
        db_listing_view = ListingView(
            listing_id=current_listing_id,
            user_id=user.id if user else None,
            viewed_at=date.today()
        )
        db.add(db_listing_view)
        await db.commit()

    if not user or (not user.is_premium and not is_moderator):
        return listing_base

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    result_all = await db.execute(
        select(func.count()).select_from(ListingViewModel).where(ListingViewModel.listing_id == current_listing_id)
    )
    viewed = result_all.scalar() or 0

    result_today = await db.execute(
        select(func.count()).select_from(ListingViewModel).where(
            (ListingViewModel.listing_id == current_listing_id) &
            (ListingViewModel.viewed_at == today)
        )
    )
    viewed_by_today = result_today.scalar() or 0

    result_per_week = await db.execute(
        select(func.count()).select_from(ListingViewModel).where(
            (ListingViewModel.listing_id == current_listing_id) &
            (ListingViewModel.viewed_at >= week_ago) &
            (ListingViewModel.viewed_at <= today)
        )
    )
    viewed_by_week = result_per_week.scalar() or 0

    result_per_month = await db.execute(
        select(func.count()).select_from(ListingViewModel).where(
            (ListingViewModel.listing_id == current_listing_id) &
            (ListingViewModel.viewed_at >= month_ago) &
            (ListingViewModel.viewed_at <= today)
        )
    )
    viewed_by_month = result_per_month.scalar() or 0

    avg_price_country = await db.scalar(
        select(func.avg(ListingModel.price_uah)).where(
            ListingModel.car_model_id == listing_base.car_model_id,
            ListingModel.country_id == listing_base.country_id
        )
    )

    if listing_base.city_id:
        avg_price_region = await db.scalar(
            select(func.avg(ListingModel.price_uah)).where(
                ListingModel.car_model_id == listing_base.car_model_id,
                ListingModel.city_id == listing_base.city_id
            )
        )
    else:
        avg_price_region = await db.scalar(
            select(func.avg(ListingModel.price_uah)).where(
                ListingModel.car_model_id == listing_base.car_model_id,
                ListingModel.region_id == listing_base.region_id
            )
        )

    listing_response = ListingResponse.model_validate(listing_base)
    listing_premium = ListingPremiumResponse(
        **listing_response.model_dump(),
        viewed=viewed,
        viewed_by_today=viewed_by_today,
        viewed_by_week=viewed_by_week,
        viewed_by_month=viewed_by_month,
        avg_price_country=avg_price_country,
        avg_price_region=avg_price_region
    )
    return listing_premium


@router.put("/{current_listing_id}", response_model=ListingResponse | MessageResponse, status_code=status.HTTP_200_OK)
async def update_listing(
        current_listing_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db),
        brand_id: int = Form(None),
        car_model_id: int = Form(None),
        country_id: int = Form(None),
        region_id: int = Form(None),
        city_id: int | None = Form(None),
        original_price: float = Form(None),
        original_currency: Currency = Form(None),
        title: str = Form(None),
        description: str | None = Form(None),
        images: list[UploadFile] | None = File(default=[]),
        dealership_id: int | None = Form(None)
):
    listing: ListingModel | None = await db.get(ListingModel, current_listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != user.id and not any([p.name == 'moderate_listings' for p in user.role.permissions]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't update this listing")

    price_uah = await create_price_uah(db, original_price, original_currency, listing)

    fields_to_update = {
        "brand_id": brand_id,
        "car_model_id": car_model_id,
        "country_id": country_id,
        "region_id": region_id,
        "city_id": city_id,
        "original_price": original_price,
        "original_currency": original_currency,
        "price_uah": price_uah,
        "title": title,
        "description": description,
        "dealership_id": dealership_id,
    }

    is_active = True
    redis_key = f"profanity_attempts:user:{user.auth_user_id}"
    if not await profanity_filter(description, title, db):
        if not await check_profanity_attempts(redis_key):
            is_active = False
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profanity check failed")
    else:
        await redis.client.delete(redis_key)

    listing.is_active = is_active

    for field, value in fields_to_update.items():
        if value is not None:
            setattr(listing, field, value)

    if images:
        storage.delete_images(listing.image_urls)
        image_urls = await storage.save_images(listing.id, images)
        listing.image_urls = image_urls

    await db.commit()
    await db.refresh(listing)

    if not listing.is_active:
        await notification_event(listing)
        return MessageResponse(message="Your listing is under moderation")

    return listing


@router.delete("/{current_listing_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_listing(
        current_listing_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db),
):
    """Delete a listing."""
    listing = await db.get(ListingModel, current_listing_id)
    await db.execute(
        delete(ListingViewModel).where(ListingViewModel.listing_id == current_listing_id)
    )
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    is_moderator = any(p.name == 'moderate_listings' for p in user.role.permissions)
    if listing.user_id != user.id and not is_moderator:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't delete this listing")
    await db.delete(listing)
    await db.commit()
    return MessageResponse(message=f"Listing {current_listing_id} deleted")
