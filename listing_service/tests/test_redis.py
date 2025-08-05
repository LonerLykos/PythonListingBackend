import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.redis import RedisClient


@pytest.mark.asyncio
async def test_get_cache_fetches_from_redis_if_exists():
    mock_redis = AsyncMock()
    mock_redis.exists.return_value = True
    mock_redis.smembers.return_value = {"badword1", "badword2"}

    with patch("app.core.redis.redis.from_url", return_value=mock_redis):
        redis_client = RedisClient()
        db = AsyncMock()

        result = await redis_client.get_cache(db)

        mock_redis.exists.assert_awaited_once_with("profanity_words")
        mock_redis.smembers.assert_awaited_once_with("profanity_words")
        assert result == {"badword1", "badword2"}


@pytest.mark.asyncio
async def test_get_cache_fetches_from_db_when_cache_miss():
    mock_redis = AsyncMock()
    mock_redis.exists.return_value = False
    mock_redis.smembers.return_value = {"badword1", "badword2"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["badword1", "badword2"]
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    with patch("app.core.redis.redis.from_url", return_value=mock_redis):
        redis_client = RedisClient()
        result = await redis_client.get_cache(mock_db)

        mock_redis.exists.assert_awaited_once()
        mock_db.execute.assert_awaited_once()
        mock_redis.sadd.assert_awaited_once_with("profanity_words", "badword1", "badword2")
        assert result == {"badword1", "badword2"}


@pytest.mark.asyncio
async def test_close():
    mock_redis = AsyncMock()
    with patch("app.core.redis.redis.from_url", return_value=mock_redis):
        redis_client = RedisClient()
        await redis_client.close()
        mock_redis.close.assert_awaited_once()
