from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Header,
    Body
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_auth_db
from app.schemas.user import (
    UserCreate,
    UserResponse,
    MessageResponse,
    UserLogin,
    NewPasswordRequest,
    RestoreRequest
)
from app.models.auth import User
from app.core.config import settings
from app.schemas.token import TokenResponse
from app.services.auth import (
    create_user,
    authenticate_user,
    create_token_pair,
    create_email_verify_token,
    verify_email,
    validate_refresh_token,
    hashing_password,
    get_current_user,
)
from shared.utils.logging import setup_logging
import shared.utils.rabbitmq as rabbitmq
from shared.utils import constants as rb_const

router = APIRouter(prefix="/api-auth", tags=["auth"])
logger = setup_logging()


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def register_user(user: UserCreate = Body(...), db: AsyncSession = Depends(get_auth_db)):
    """Register a new user and send a verification email."""
    db_user = await create_user(db, user.email, user.password, user.username)
    token = await create_email_verify_token(db, db_user)
    await rabbitmq.publish_event(
        rb_const.RABBITMQ_QUEUE_EMAIL_EVENTS,
        rb_const.EVENT_EMAIL_SEND,
        {
            "email": db_user.email,
            "subject": "Verify Your Account",
            "template_name": "register.html",
            "context": {
                "verify_url": f'{settings.frontend_url}/verify-email/{token}',
                "username": db_user.username,
            }
        }
    )
    logger.info("User registered, verification email sent", user_id=db_user.id, email=db_user.email,
                username=db_user.username)
    return MessageResponse(message="Please check your email to verify your account")


@router.post("/verify-email", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def verify_email_endpoint(
        request: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_auth_db)):
    """Verify user`s email by token"""
    user = await verify_email(db, request.split(' ')[1], 'create_user')
    logger.info(f"User {user.id} verified")
    return MessageResponse(message='You have been verified. Login to continue.')


@router.post("/login", response_model=TokenResponse, summary="Login with email", status_code=status.HTTP_200_OK)
async def login(
        form_data: UserLogin = Body(...),
        db: AsyncSession = Depends(get_auth_db)):
    """Authenticate user and return token`s pair"""
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_auth_token = await create_token_pair(db, user)
    logger.info("User logged in", user_id=user.id, email=user.email, username=user.username)
    return TokenResponse(access_token=access_token, refresh_token=refresh_auth_token)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
        refresh_auth_token: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_auth_db)):
    """Refresh user`s auth token pair"""
    user, new_access_token, new_refresh_token = await validate_refresh_token(db, refresh_auth_token.split(' ')[1])
    logger.info("Token refreshed", user_id=user.id, email=user.email, username=user.username)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get("/users", response_model=list[UserResponse])
async def get_auth_users(
        token: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_auth_db)):
    """Get all auth users"""
    user = await get_current_user(token.split(' ')[1], db )
    if not user.is_superadmin:
        logger.error("User is not superadmin")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    result = await db.execute(select(User))
    all_auth_users = result.scalars().all()
    return all_auth_users


@router.post("/restore-request", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def restore_request(email: RestoreRequest = Body(...), db: AsyncSession = Depends(get_auth_db)):
    db_user = await db.scalar(select(User).where(User.email == email.email))
    if db_user:
        token = await create_email_verify_token(db, db_user)
        await rabbitmq.publish_event(
            rb_const.RABBITMQ_QUEUE_EMAIL_EVENTS,
            rb_const.EVENT_EMAIL_SEND,
            {
                "email": db_user.email,
                "subject": "Request for changing password",
                "template_name": "restore_pass.html",
                "context": {
                    "restore_url": f'{settings.frontend_url}/restore-password/{token}',
                    "username": db_user.username,
                }
            }
        )
        logger.info(f'User {db_user.id} send restore password request')

    return MessageResponse(message=f"We send message on {email.email} to restore your password")


@router.patch("/restore-password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def restore_password(
        password: NewPasswordRequest = Body(...),
        request: str = Header(..., alias="Authorization"),
        db: AsyncSession = Depends(get_auth_db)):
    """Restore user`s password"""
    user = await verify_email(db, request.split(' ')[1])
    hashed_password = await hashing_password(password.new_password)
    user.password_hash = hashed_password
    await db.commit()
    logger.info(f"User's {user.id} password restored")
    return MessageResponse(message="Password restored, login to continue")
