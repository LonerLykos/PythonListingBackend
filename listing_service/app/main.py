from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.api.listings import router as listings_router
from app.api.roles import router as roles_router
from app.api.permissions import router as permissions_router
from app.api.role_permissions import router as role_permissions_router
from app.api.users import router as users_router
from app.api.regions import router as regions_router
from app.api.profanity_words import router as profanity_words_router
from app.api.cars import router as cars_router
import asyncio
import os
from shared.utils.logging import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Auth Service is starting...")

    engine = create_async_engine(settings.listing_db_url, echo=False)

    max_attempts = 20
    delay = 3.0
    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("Database connection established.")
                break
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt == max_attempts:
                logger.error("Max attempts reached. Exiting.")
                raise RuntimeError("Database is not available.")
            await asyncio.sleep(delay)

    logger.info("Running Alembic migrations...")
    result = os.system("alembic upgrade head")
    if result != 0:
        logger.error("Alembic migrations failed")
        raise RuntimeError("Migration failed")
    logger.info("Alembic migrations applied.")

    yield

    logger.info("Auth Service is shutting down...")

app = FastAPI(
    title="Listing Service",
    version="1.0",
    lifespan=lifespan,
    reload=True,
    redirect_slashes=False
)

app.include_router(listings_router, prefix="/api-listings")
app.include_router(roles_router, prefix="/api-listings")
app.include_router(permissions_router, prefix="/api-listings")
app.include_router(role_permissions_router, prefix="/api-listings")
app.include_router(users_router, prefix="/api-listings")
app.include_router(regions_router, prefix="/api-listings")
app.include_router(profanity_words_router, prefix="/api-listings")
app.include_router(cars_router, prefix="/api-listings")

app.mount(
    settings.media_url,
    StaticFiles(directory=settings.media_root),
    name="media"
)
