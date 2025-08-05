import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.profanity_words import ProfanityWords


class RedisClient:
    def __init__(self, redis_url: str = settings.redis_url):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.key = "profanity_words"
        self.ttl = 3600  # seconds

    async def set_cache(self, db: AsyncSession) -> None:
        """Saving bad words in Redis"""
        words = await self._get_profanity_words_from_db(db)
        if words:
            await self.client.delete(self.key)
            await self.client.sadd(self.key, *words)
            await self.client.expire(self.key, self.ttl)

    async def get_cache(self, db: AsyncSession) -> set[str]:
        """Get words from Redis"""
        exists = await self.client.exists(self.key)
        if not exists:
            await self.set_cache(db)
        return await self.client.smembers(self.key)

    @staticmethod
    async def _get_profanity_words_from_db(db: AsyncSession) -> list[str]:
        """Get words from DB"""
        result = await db.execute(select(ProfanityWords.word))
        return list(result.scalars().all())

    async def close(self):
        """Close Redis's connection"""
        await self.client.close()


redis_client = RedisClient()
