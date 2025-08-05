from datetime import timedelta, date
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status, Body
)
from sqlalchemy import select
from app.schemas.role import RoleId
from app.schemas.user import (
    User as UserResponse
)
from app.models.user import User as UserModel, Role as RoleModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.services.user_manager import user_manager
from app.utils.token_utils import get_user_from_token
from shared.utils.logging import setup_logging

logger = setup_logging()

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_all_users(
        user: UserModel = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'ban_user')
    result = await db.execute(select(UserModel))
    return result.scalars().all()


@router.patch("/premium", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def become_premium_user(
        user: UserModel = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    user.is_premium = True
    user.premium_expires_at = date.today()+ timedelta(days=30)
    await db.commit()
    await db.refresh(user)
    return user


@router.get('/me', response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(user: UserModel = Depends(get_user_from_token)):
    return user


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_user_by_id(
        user_id: int,
        user: UserModel = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'ban_user')
    user_by_id = await db.get(UserModel, user_id)
    if not user_by_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_by_id


@router.patch("/{user_id}/banned", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def banned_user_by_id(
        user_id: int,
        user: UserModel = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)
):
    await permission_checker(user, 'ban_user')
    target: UserModel | None = await db.get(UserModel, user_id)
    if await user_manager(user, target, db, 'toggle_ban_status'):
        target.is_banned = not target.is_banned
        await db.commit()
        return target
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.patch('/{user_id}/change-role', response_model=UserResponse, status_code=status.HTTP_200_OK)
async def change_user_role(
        user_id: int,
        role_id: RoleId,
        user: UserModel = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)
):
    await permission_checker(user, 'changing_user_role')
    target: UserModel | None = await db.get(UserModel, user_id)
    if await user_manager(user, target, db, 'changing role'):
        role_by_id = await db.get(RoleModel, role_id.role_id)
        if not role_by_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        target.role_id = role_id.role_id
        await db.commit()
        return target
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
