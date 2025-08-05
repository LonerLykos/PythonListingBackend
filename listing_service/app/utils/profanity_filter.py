import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import redis_client
from better_profanity import profanity
from shared.utils.logging import setup_logging

logger = setup_logging()


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


async def profanity_filter(
        description: str | None,
        title: str | None,
        db: AsyncSession) ->bool:
    """Filter profanity words from description and title"""
    description = (description or '').lower()
    title = (title or '').lower()
    desc_words = tokenize(description)
    title_words = tokenize(title)
    redis_words = await redis_client.get_cache(db)
    profanity.load_censor_words()
    extended_words = set(str(w) for w in profanity.CENSOR_WORDSET).union(redis_words)
    all_censor_words = {w.lower() for w in extended_words}

    return desc_words.isdisjoint(all_censor_words) and title_words.isdisjoint(all_censor_words)
