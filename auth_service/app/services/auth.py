from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.db.database import get_auth_db
from app.models.auth import User, ActiveToken, BlacklistedToken, TokenType
from shared.utils import publish_event, setup_logging, constants as rb_const

logger = setup_logging()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hashing_password(password: str) -> str:
    return pwd_context.hash(password)


async def create_user(db: AsyncSession, email: str, password: str, username: str) -> User:
    """Create a new user"""
    result = await db.execute(select(User).where((User.email == email) | (User.username == username)))
    db_user = result.scalars().first()
    if db_user:
        if db_user.email == email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    hashed_password = await hashing_password(password)
    db_user = User(email=email, password_hash=hashed_password, username=username, is_active=False)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Verify data for login"""
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not pwd_context.verify(password, user.password_hash) or not user.is_active:
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get user by id"""
    user = await db.scalar(select(User).where(User.id == user_id, User.is_active == True))
    return user


async def decode_token(token: str, secret_key: str, algorithm: str) -> int:
    """Decoding the token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=algorithm)
        if payload.get('sub') is None:
            logger.error(f"Invalid token: {token}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You need to be logged")
        user_id: int = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found."
            )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except JWTError as e:
        print('JWT error', e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"You need to be logged."
        )
    return user_id


async def create_tokens(token_type: TokenType, expire_at: int, email: str, pk: int, db: AsyncSession) -> str:
    """Generate a new token"""
    if token_type == TokenType.AUTH_ACCESS:
        expire = datetime.now(timezone.utc) + timedelta(hours=expire_at)
        secret = settings.access_token_secret_key
        token_type = TokenType.AUTH_ACCESS
    elif token_type == TokenType.AUTH_REFRESH:
        expire = datetime.now(timezone.utc) + timedelta(days=expire_at)
        secret = settings.refresh_token_secret_key
        token_type = TokenType.AUTH_REFRESH
    elif token_type == TokenType.EMAIL_VERIFY:
        expire = datetime.now(timezone.utc) + timedelta(hours=expire_at)
        secret = settings.email_verify_secret_key
        token_type = TokenType.EMAIL_VERIFY
    else:
        logger.error(f"Invalid token type: {token_type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Something went wrong.'
        )

    to_encode = {
        "sub": str(pk),
        "email": email,
        "time": str(datetime.now(timezone.utc)),
        "exp": expire
    }
    token = jwt.encode(to_encode, secret, algorithm=settings.algorithm)

    db_token = ActiveToken(
        token=token,
        user_id=pk,
        token_type=token_type,
        expires_at=expire,
    )
    db.add(db_token)
    await db.commit()
    return token


async def get_current_user(
        token: str,
        db: AsyncSession = Depends(get_auth_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    await token_checker(db, token, credentials_exception, TokenType.AUTH_ACCESS)

    user_id = await decode_token(
        token,
        settings.access_token_secret_key,
        settings.algorithm
    )

    user = await get_user_by_id(db, user_id)

    if user is None:
        raise credentials_exception

    return user


async def create_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create a new token pair"""
    access_token = await create_tokens(
        TokenType.AUTH_ACCESS,
        settings.access_token_expire_hours,
        user.email,
        user.id,
        db,
    )
    refresh_token = await create_tokens(
        TokenType.AUTH_REFRESH,
        settings.refresh_token_expire_days,
        user.email,
        user.id,
        db,
    )

    return access_token, refresh_token


async def create_email_verify_token(db: AsyncSession, user: User) -> str:
    """Create an email verification token."""
    return await create_tokens(
        TokenType.EMAIL_VERIFY,
        settings.email_verify_expire_hours,
        user.email,
        user.id,
        db
    )


async def token_to_blacklist(db: AsyncSession, token: ActiveToken) -> None:
    blacklisted = BlacklistedToken(
        token=token.token,
    )
    db.add(blacklisted)
    await db.commit()


async def token_checker(db: AsyncSession, token:str, credentials, token_type: TokenType) -> ActiveToken | None:
    blacklisted_token = await db.scalar(select(BlacklistedToken).where(BlacklistedToken.token == token))

    if blacklisted_token:
        raise credentials

    db_token = await db.scalar(select(ActiveToken).where(
        ActiveToken.token == token,
        ActiveToken.token_type == token_type
    ))

    if not db_token:
        raise credentials

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        await token_to_blacklist(db, db_token)
        await db.delete(db_token)
        await db.commit()
        raise credentials

    return db_token


async def verify_email(db: AsyncSession, token: str, task: str | None = None) -> User:
    """Verify email with token, activate user, publish event."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You need register again.",
    )

    db_token = await token_checker(db, token, credentials_exception, TokenType.EMAIL_VERIFY)
    user_id = await decode_token(db_token.token, settings.email_verify_secret_key, settings.algorithm)
    user: User | None = await db.scalar(select(User).where(User.id == user_id))

    if not user:
        raise credentials_exception
    user.is_active = True
    await token_to_blacklist(db, db_token)
    await db.delete(db_token)
    await db.commit()
    await db.refresh(user)

    if task and task == 'create_user':
        await publish_event(rb_const.RABBITMQ_QUEUE_USER_EVENTS, rb_const.EVENT_USER_CREATED, {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_superadmin": user.is_superadmin
        })
    return user


async def validate_refresh_token(db: AsyncSession, refresh_token: str) -> tuple[User, str, str]:
    """Validate refresh token and return new token pair"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Something wrong. Try again or relogin.",
    )

    db_token = await token_checker(db, refresh_token, credentials_exception, TokenType.AUTH_REFRESH)
    user_id = await decode_token(db_token.token, settings.refresh_token_secret_key, settings.algorithm)
    user: User | None = await get_user_by_id(db, user_id)

    if user is None:
        raise credentials_exception
    await token_to_blacklist(db, db_token)
    await db.delete(db_token)

    new_access_token, new_refresh_token = await create_token_pair(db, user)
    await db.commit()
    return user, new_access_token, new_refresh_token
