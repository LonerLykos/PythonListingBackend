from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_auth_db
from app.main import app
from app.models.auth import User, ActiveToken, TokenType
from app.schemas.user import UserCreate


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
def override_db_dependency(mock_db):
    async def _override():
        yield mock_db
    app.dependency_overrides[get_auth_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def user_factory():
    def _create_user(user_type: str):
        if user_type == "test_inactive_user":
            return User(
                id=1,
                password_hash='hash_password',
                email="test1@example.com",
                is_active=False,
                username="Test1",
                is_superadmin=False,
            )
        elif user_type == "test_active_user":
            return User(
                id=2,
                password_hash='hash_password',
                email="test2@example.com",
                is_active=True,
                username="Test2",
                is_superadmin=False,
            )
        elif user_type == "test_admin_user":
            return User(
                id=3,
                password_hash='hash_password',
                email="test3@example.com",
                is_active=True,
                is_superadmin=True,
                username="Test3"
            )
        elif user_type == "schema_user":
            return UserCreate(
                email="test@example.com",
                password="Te7sP@ss",
                username="Testuser"
            )
        else:
            return None
    return _create_user


@pytest.fixture
def token_factory():
    def _create_token(token_type: str):
        if token_type == "access":
            return ActiveToken(
                id=1,
                token_type=TokenType.AUTH_ACCESS,
                token="test_access_token",
                user_id=1,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        elif token_type == "refresh":
            return ActiveToken(
                id=2,
                token_type=TokenType.AUTH_REFRESH,
                token="test_refresh_token",
                user_id=1,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        elif token_type == 'verify':
            return ActiveToken(
                id=3,
                token_type=TokenType.EMAIL_VERIFY,
                token="test_verify_token",
                user_id=1,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
        else:
            return None

    return _create_token
