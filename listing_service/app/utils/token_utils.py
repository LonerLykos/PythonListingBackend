from jose import jwt, JWTError
from datetime import datetime, timezone, date
from fastapi import HTTPException, Header, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from shared.utils.logging import setup_logging
from app.core.config import settings
from app.db.database import get_listing_db
from app.models.user import User, Role

logger = setup_logging()


async def get_user_from_token(
        authorization: str = Header(..., alias='Authorization'),
        db: AsyncSession = Depends(get_listing_db)) -> User:
    """Get, decode and verify token, return user"""
    if not authorization.startswith("Bearer"):
        logger.error("Bearer token not found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You need to login.")

    try:
        payload = jwt.decode(
            authorization[7:],
            settings.access_token_secret_key,
            algorithms=settings.algorithm
        )

        exp = payload.get("exp")
        if not exp:
            logger.error("Token payload missing exp")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'You need tobe logged')

        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            logger.error("Token expired")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'You need to be logged')

        user_id = payload.get("sub")
        email = payload.get("email")
        if not email or not user_id:
            logger.error("Token payload missing email or user_id")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'You need to be logged')

        user = await db.scalar(select(User).where(User.auth_user_id == int(user_id)).options(
            selectinload(User.role).selectinload(Role.permissions)
        ))

        if not user or user.email != email:
            logger.error("User not found or email mismatch")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'You need to be logged')

        if user.is_banned:
            logger.error("User banned")
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'Your account is banned')

        today = date.today()
        if user.is_premium and user.premium_expires_at < today:
            user.is_premium = False
            user.premium_expires_at = None
            await db.commit()
            await db.refresh(user)

        return user

    except JWTError as e:
        logger.error(f'JWT decoding error: {e}')
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'You need to login')


async def get_optional_user_from_token(
        authorization: str | None = Header(None, alias='Authorization'),
        db: AsyncSession = Depends(get_listing_db)
) -> User | None:
    if not authorization:
        return None
    return await get_user_from_token(authorization, db)
