from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User as UserModel
from shared.utils.logging import setup_logging

logger = setup_logging()


async def user_manager(performer: UserModel, target: UserModel | None, db: AsyncSession, task: str) -> bool:
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if performer.id == target.id:
        logger.error(f'User {performer.username} ID: {performer.id}, trying to {task} for himself')
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
    if performer.is_superadmin and not target.is_superadmin:
        return True
    if performer.role_id == 1 and target.role_id != 1:
        return True
    if performer.role_id == 2 and target.role_id == 3 and task.lower() == 'toggle_ban_status':
        return True

    if task == 'changing role':
        logger.error(f'Admin {performer.id} trying to {task} for another admin')
    if task == 'toggle_ban_status':
        if performer.role_id == 1:
            logger.error(f'Admin {performer.id} trying to {task} for another admin')
        if performer.role_id == 2:
            logger.error(f'Manager {performer.id} trying to {task} for another manager')
    return False
