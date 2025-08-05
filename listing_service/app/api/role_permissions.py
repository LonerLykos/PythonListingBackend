from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from app.schemas.role_permission import (
    RolePermissionBase,
    RolePermission as RolePermissionResponse,
)
from app.schemas.listing import MessageResponse
from app.models.user import User, RolePermission as RolePermissionModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/role-permissions", tags=["role_permissions"])


@router.get('', response_model=list[RolePermissionResponse], status_code=status.HTTP_200_OK)
async def get_all_role_permissions(
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_role_permission_pair')
    result = await db.execute(select(RolePermissionModel))
    role_permissions = result.scalars().all()
    return role_permissions


@router.post('', response_model=RolePermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_role_permission(
        role_permission_data: RolePermissionBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_role_permission_pair')
    role_permission_checker =await db.scalar(
        select(RolePermissionModel)
        .where(RolePermissionModel.role_id == role_permission_data.role_id)
        .where(RolePermissionModel.permission_id == role_permission_data.permission_id)
    )

    if role_permission_checker:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role_Permission pair already exists")

    db_role_permission = RolePermissionModel(
        role_id=role_permission_data.role_id,
        permission_id=role_permission_data.permission_id
    )
    db.add(db_role_permission)
    await db.commit()
    await db.refresh(db_role_permission)
    return db_role_permission


@router.get('/{role_permission_id}', response_model=RolePermissionResponse, status_code=status.HTTP_200_OK)
async def get_role_permission(
        role_permission_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_role_permission_pair')
    role_permission = await db.get(RolePermissionModel, role_permission_id)
    if not role_permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role_Permission pair not found")
    return role_permission


@router.delete('/{role_permission_id}',response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_role_permission(
        role_permission_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_role_permission_pair')
    role_permission = await db.get(RolePermissionModel, role_permission_id)
    if not role_permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role_Permission pair not found")
    await db.delete(role_permission)
    await db.commit()
    return MessageResponse(message=f"Role_Permission_Pair {role_permission_id} deleted")
