from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from app.schemas.permission import (
    PermissionBase,
    Permission as PermissionResponse,
    PermissionUpdate,
)
from app.schemas.listing import MessageResponse
from app.models.user import User, Permission as PermissionModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get('', response_model=list[PermissionResponse], status_code=status.HTTP_200_OK)
async def get_all_permissions(
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    result = await db.execute(select(PermissionModel))
    permissions = result.scalars().all()
    return permissions


@router.post('', response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
        permission_data: PermissionBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    if await db.scalar(select(PermissionModel).where(PermissionModel.name == permission_data.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Permission already exists')
    db_permission = PermissionModel(
        name=permission_data.name,
        description=permission_data.description or None
    )
    db.add(db_permission)
    await db.commit()
    await db.refresh(db_permission)
    return db_permission


@router.get('/{permission_id}', response_model=PermissionResponse, status_code=status.HTTP_200_OK)
async def get_permission_by_id(
        permission_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)
):
    await permission_checker(user, 'manage_roles_and_permissions')
    permission = await db.get(PermissionModel, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Permission not found')
    return permission


@router.put('/{permission_id}', response_model=PermissionResponse, status_code=status.HTTP_200_OK)
async def get_permission_by_id(
        permission_id: int,
        permission_data: PermissionUpdate,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)
):
    await permission_checker(user, 'manage_roles_and_permissions')
    permission = await db.get(PermissionModel, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Permission not found')

    permission.name = permission_data.name or permission.name
    permission.description = permission_data.description or permission.description
    await db.commit()
    return permission


@router.delete('/{permission_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_role_by_id(
        permission_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    permission = await db.get(PermissionModel, permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Permission not found')
    await db.delete(permission)
    await db.commit()
    return MessageResponse(message=f"Permission {permission_id} deleted")
