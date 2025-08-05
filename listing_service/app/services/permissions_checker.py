from fastapi import HTTPException, status
from app.models.user import User
from shared.utils.logging import setup_logging

logger = setup_logging()


async def permission_checker(user: User, text:str) -> None:
    if not any(p.name == text for p in user.role.permissions):
        logger.error(f'User {user.id} does not have {text} permission')
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
