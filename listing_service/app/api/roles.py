from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from app.schemas.role import (
    RoleBase,
    Role as RoleResponse
)
from app.schemas.listing import MessageResponse
from app.models.user import User, Role as RoleModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get('', response_model=list[RoleResponse], status_code=status.HTTP_200_OK)
async def get_all_roles(
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    result = await db.execute(select(RoleModel))
    roles = result.scalars().all()
    return roles


@router.post('', response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
        role: RoleBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    if await db.scalar(select(RoleModel).where(RoleModel.name == role.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Role already exists')
    db_role = RoleModel(
        name=role.name,
    )
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role


@router.get('/{role_id}', response_model=RoleResponse, status_code=status.HTTP_200_OK)
async def get_role_by_id(
        role_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)
):
    await permission_checker(user, 'manage_roles_and_permissions')
    role = await db.get(RoleModel, role_id)
    if not role:
        raise HTTPException(status_code=404, detail='Role not found')
    return role


@router.delete('/{role_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_role_by_id(
        role_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_roles_and_permissions')
    role = await db.get(RoleModel, role_id)
    if not role:
        raise HTTPException(status_code=404, detail='Role not found')
    await db.delete(role)
    await db.commit()
    return MessageResponse(message=f"Role {role_id} deleted")
