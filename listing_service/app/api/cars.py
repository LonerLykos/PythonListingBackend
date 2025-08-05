from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.schemas.car import (
    BrandBase,
    Brand as BrandResponse,
    CarModelBase,
    CarModel as CarModelResponse,
    CarModelInBrand,
    BrandWithModels
)
from app.schemas.listing import MessageResponse
from app.models.user import User
from app.models.car import Brand as BrandModel, CarModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/cars", tags=["cars"])


@router.get('/brands', response_model=list[BrandResponse], status_code=status.HTTP_200_OK)
async def get_brands(
        db: AsyncSession = Depends(get_listing_db)):
    brands = await db.execute(select(BrandModel))
    return brands.scalars().all()


@router.post('/brands', response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
        brand: BrandBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_cars')
    if await db.scalar(select(BrandModel).where(BrandModel.name == brand.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Brand already exists")
    db_brand = BrandModel(
        name=brand.name,
    )
    db.add(db_brand)
    await db.commit()
    await db.refresh(db_brand)
    return db_brand


@router.delete('/brands/{brand_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_brand(
        brand_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_cars')
    db_brand = await db.get(BrandModel, brand_id)
    if not db_brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    await db.delete(db_brand)
    await db.commit()
    return MessageResponse(message=f"Brand {brand_id} deleted")


@router.get('/brand-with-models/{brand_id}', response_model=BrandWithModels, status_code=status.HTTP_200_OK)
async def get_brand_with_models(
        brand_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    brand_with_models = await db.scalar(select(BrandModel).options(selectinload(BrandModel.car_models)).where(BrandModel.id == brand_id))
    if brand_with_models is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand_with_models


@router.get('/models', response_model=list[CarModelResponse], status_code=status.HTTP_200_OK)
async def get_all_models(
        db: AsyncSession = Depends(get_listing_db)):
    models = await db.execute(select(CarModel))
    return models.scalars().all()


@router.post('/models', response_model=CarModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
        model: CarModelBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_cars')
    checker_model_name: BrandWithModels | None = await db.scalar(select(BrandModel).options(selectinload(BrandModel.car_models)).where(BrandModel.id == model.brand_id))
    if not checker_model_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    model_names = [m.name.lower() for m in checker_model_name.car_models]
    if model.name.lower() in model_names:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model with this name already exists for the brand"
        )

    db_model = CarModel(
        name=model.name,
        brand_id=model.brand_id
    )
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    return db_model


@router.delete('/models/{model_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_model(
        model_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_cars')
    db_model = await db.get(CarModel, model_id)
    if not db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    await db.delete(db_model)
    await db.commit()
    return MessageResponse(message=f"Model {model_id} deleted")


@router.get('/models-by-brand/{brand_id}', response_model=list[CarModelInBrand], status_code=status.HTTP_200_OK)
async def get_by_brand(
        brand_id: int,
        db: AsyncSession = Depends(get_listing_db)):
    db_brand = await db.scalar(select(BrandModel).options(selectinload(BrandModel.car_models)).where(BrandModel.id == brand_id))
    if not db_brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return db_brand.car_models
