import tempfile
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from pathlib import Path
from app.core.config import settings
from app.models.listing import Currency, Listing as ListingModel
from app.utils.create_price_uah import create_price_uah
from app.utils.profanity_filter import profanity_filter
from app.utils.storage import Storage
from app.utils.token_utils import get_optional_user_from_token, get_user_from_token
from app.schemas.additional_request import (
    AddEntityRequest,
    AddCountry,
    AddRegion,
    AddCity,
    AddBrand,
    AddCarModel
)
from app.models.region import (
    Country as CountryModel,
    Region as RegionModel
)
from app.models.car import Brand as BrandModel, CarModel
from app.utils.additional_checker import additional_checker


@pytest.mark.asyncio
async def test_get_optional_user_from_token_without_user(mock_db):
    result = await get_optional_user_from_token(None, mock_db)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_from_token(mock_db, listing_user_factory):
    token = "Bearer token"
    user = listing_user_factory('test_user_with_permission')
    valid_payload = {
        "sub": "123",
        "email": "test6@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }

    with patch("app.utils.token_utils.jwt.decode", return_value=valid_payload):
        mock_db.scalar.return_value = user

        result = await get_user_from_token(token, db=mock_db)
        assert result == user
        assert result.is_premium is True
        mock_db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_from_token_invalid_header():
    with pytest.raises(HTTPException) as exc_info:
        await get_user_from_token("Invalid token")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "You need to login."


@pytest.mark.asyncio
async def test_get_user_from_token_expired(mock_db):
    expired_payload = {
        "sub": "123",
        "email": "test@example.com",
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    }

    with patch("app.utils.token_utils.jwt.decode", return_value=expired_payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token("Bearer token", db=mock_db)
    assert exc_info.value.status_code == 401
    assert "logged" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()), "email": None, "sub": "123"},
    {"exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()), "email": "email@example.com", "sub": None},
])
async def test_get_user_from_token_missing_fields(payload, mock_db):
    with patch("app.utils.token_utils.jwt.decode", return_value=payload):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token("Bearer token", db=mock_db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_token_user_not_found(mock_db):
    payload = {
        "sub": "123",
        "email": "test@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    with patch("app.utils.token_utils.jwt.decode", return_value=payload):
        mock_db.scalar.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token("Bearer token", db=mock_db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_user_from_token_banned_user(listing_user_factory, mock_db):
    payload = {
        "sub": "123",
        "email": "test5@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    user = listing_user_factory('test_banned_user')

    with patch("app.utils.token_utils.jwt.decode", return_value=payload):
        mock_db.scalar.return_value = user

        with pytest.raises(HTTPException) as exc_info:
            await get_user_from_token("Bearer token", db=mock_db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_save_images_creates_and_returns_urls(mock_upload_file_jpg):
    with tempfile.TemporaryDirectory() as tmp_media:
        storage = Storage(media_root=tmp_media)
        listing_id = 42

        result_urls = await storage.save_images(listing_id, [mock_upload_file_jpg])

        assert len(result_urls) == 1
        saved_path = Path(tmp_media) / f"listings/{listing_id}"
        files = list(saved_path.iterdir())

        assert len(files) == 1
        assert files[0].exists()
        assert result_urls[0].endswith(f"/listings/{listing_id}/{files[0].name}")


@pytest.mark.unit
def test_delete_images_removes_files(mock_upload_file_jpg):
    with tempfile.TemporaryDirectory() as tmp_media:
        storage = Storage(media_root=tmp_media)
        listing_id = 42
        file_name = "mock.jpg"
        listing_dir = Path(tmp_media) / f"listings/{listing_id}"
        listing_dir.mkdir(parents=True)
        file_path = listing_dir / file_name
        file_path.write_bytes(b"mock content")

        assert file_path.exists()

        media_url = settings.media_url.rstrip("/")
        url = f"{media_url}/listings/{listing_id}/{file_name}"

        storage.delete_images([url])
        assert not file_path.exists()


@pytest.mark.asyncio
async def test_profanity_filter_clean_text(mock_db, mock_censor_words):
    with patch("app.utils.profanity_filter.redis_client.get_cache", new_callable=AsyncMock) as mock_redis:
        mock_redis.return_value = set()

        mock_censor_words.clear()

        description = "This is a nice car"
        title = "Best offer"

        result = await profanity_filter(description, title, mock_db)

        assert result is True
        mock_redis.assert_awaited_once_with(mock_db)


@pytest.mark.asyncio
async def test_profanity_filter_detects_in_description(mock_db, mock_censor_words):
    with patch("app.utils.profanity_filter.redis_client.get_cache", new_callable=AsyncMock) as mock_redis:
        mock_redis.return_value = {"badword"}

        mock_censor_words.clear()
        mock_censor_words.extend({"stupid", "ugly"})

        description = "This is stupid and ugly"
        title = "Clean title"

        result = await profanity_filter(description, title, mock_db)

        assert result is False
        mock_redis.assert_awaited_once_with(mock_db)


@pytest.mark.asyncio
async def test_profanity_filter_detects_in_title(mock_db, mock_censor_words):
    with patch("app.utils.profanity_filter.redis_client.get_cache", new_callable=AsyncMock) as mock_redis:
        mock_redis.return_value = {"insult"}

        mock_censor_words.clear()
        mock_censor_words.extend({"insult"})

        description = "Nice car"
        title = "This title contains insult"

        result = await profanity_filter(description, title, mock_db)

        assert result is False
        mock_redis.assert_awaited_once_with(mock_db)


@pytest.mark.asyncio
@pytest.mark.parametrize("price,currency,expected", [
    (100, Currency.UAH, 100),
    (100, Currency.USD, 4000),
    (100, Currency.EUR, 4400),
])
async def test_create_price_uah_without_listing(mock_exchange_rate, price, currency, expected, mock_db):
    mock_db.scalar.return_value = mock_exchange_rate

    result = await create_price_uah(mock_db, price, currency)
    assert result == expected


@pytest.mark.asyncio
async def test_create_price_uah_with_same_listing_data(mock_exchange_rate, mock_db):
    mock_db.scalar.return_value = mock_exchange_rate

    listing = ListingModel(
        original_price=100,
        original_currency=Currency.USD,
    )
    result = await create_price_uah(mock_db, 100, Currency.USD, listing)
    assert result is None


@pytest.mark.asyncio
async def test_create_price_uah_only_listing_given(mock_exchange_rate, mock_db):
    mock_db.scalar.return_value = mock_exchange_rate

    listing = ListingModel(
        original_price=100,
        original_currency=Currency.EUR,
        price_uah=4400
    )
    result = await create_price_uah(mock_db, None, None, listing)
    assert result == 4400


@pytest.mark.asyncio
async def test_create_price_uah_only_original_price_given(mock_exchange_rate, mock_db):
    mock_db.scalar.return_value = mock_exchange_rate

    listing = ListingModel(
        original_price=200,
        original_currency=Currency.USD,
    )
    result = await create_price_uah(mock_db, 200, None, listing)
    assert result == 8000


@pytest.mark.asyncio
async def test_create_price_uah_only_original_currency_given(mock_exchange_rate, mock_db):
    mock_db.scalar.return_value = mock_exchange_rate

    listing = ListingModel(
        original_price=300,
        original_currency=Currency.EUR,
    )
    result = await create_price_uah(mock_db, None, Currency.EUR, listing)
    assert result == 13200


@pytest.mark.asyncio
async def test_create_price_uah_no_exchange_rates(mock_db):
    mock_db.scalar.return_value = None

    result = await create_price_uah(mock_db, 100, Currency.USD)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize("request_obj, existing_in_db, should_raise", [
    # Country already exists
    (AddCountry(type="add_country", name="Ukraine"), CountryModel(id=1, name="Ukraine"), True),

    # Country does not exist
    (AddCountry(type="add_country", name="Ukraine"), None, False),

    # Region already exists under country
    (AddRegion(type="add_region", name="Lviv", country_name="Ukraine"),
            CountryModel(
                id=1,
                name="Ukraine",
                regions=[RegionModel(id=1, name="Lviv", country_id=1)]
            ),
            True
    ),

    # Region does not exist
    (AddRegion(type="add_region", name="Kyiv", country_name="Ukraine"),
            CountryModel(
                id=1,
                name="Ukraine",
                regions=[]
            ),
            False
    ),

    # Brand exists
    (AddBrand(type="add_brand", name="BMW"), BrandModel(id=1, name="BMW"), True),

    # Car model already exists
    (AddCarModel(type="add_carmodel", name="M5", brand_name="BMW"),
            BrandModel(
                id=1,
                name="BMW",
                car_models=[CarModel(id=1, name="M5", brand_id=1)]
            ),
            True
    ),

    # Car model does not exist
    (AddCarModel(type="add_carmodel", name="M4", brand_name="BMW"),
            BrandModel(
                id=1,
                name="BMW",
                car_models=[]
            ),
            False
    ),
])
@patch("app.utils.additional_checker.creating_event", new_callable=AsyncMock)
@patch("app.utils.additional_checker.normalize_name", side_effect=lambda x: x.lower())
async def test_additional_checker(
        mock_db,
        mock_create_event,
        request_obj,
        existing_in_db,
        should_raise):

    async def mock_scalar(query):
        if isinstance(request_obj, AddCountry):
            return existing_in_db if existing_in_db and isinstance(existing_in_db, CountryModel) else None
        if isinstance(request_obj, AddRegion):
            return existing_in_db if isinstance(existing_in_db, CountryModel) else None
        if isinstance(request_obj, AddBrand):
            return existing_in_db if isinstance(existing_in_db, BrandModel) else None
        if isinstance(request_obj, AddCarModel):
            return existing_in_db if isinstance(existing_in_db, BrandModel) else None
        return None

    mock_db.scalar.side_effect = mock_scalar

    if should_raise:
        with pytest.raises(HTTPException):
            await additional_checker(user_id=1, request=request_obj, db=mock_db)
        mock_create_event.assert_not_awaited()
    else:
        await additional_checker(user_id=1, request=request_obj, db=mock_db)
        mock_create_event.assert_awaited_once()
