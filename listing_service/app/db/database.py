from contextlib import asynccontextmanager
from app.core.config import settings
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)

engine = create_async_engine(settings.listing_db_url, echo=True)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_listing_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_listing_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
