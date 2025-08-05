from app.core.config import settings
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

engine = create_async_engine(settings.auth_db_url, echo=True)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_auth_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
