from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.api.auth import router as auth_router
from app.core.config import settings
from shared.utils.logging import setup_logging
import asyncio
import os

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Auth Service is starting...")

    engine = create_async_engine(settings.auth_db_url, echo=False)

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
    title="Auth Service",
    version="1.0.0",
    lifespan=lifespan,
    reload=True,
    redirect_slashes=False
)

app.include_router(auth_router)
