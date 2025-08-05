import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, status
from app.core.redis import redis_client
from app.models import User as UserModel
from app.services.listing import (
    validate_references,
    check_profanity_attempts,
    create_listing_service
)
from app.services.permissions_checker import permission_checker
from app.services.user_manager import user_manager


@pytest.mark.asyncio
async def test_permission_checker(listing_user_factory):
    user = listing_user_factory('test_user_with_permission')
    text1 = 'moderate_listings'
    text2 = 'some_another_permission'

    result1 = await permission_checker(user, text1)
    assert result1 is None

    with pytest.raises(HTTPException) as exc_info:
        await permission_checker(user, text2)

    exc = exc_info.value
    assert exc.status_code == status.HTTP_403_FORBIDDEN
    assert exc.detail == 'Access denied'


@pytest.mark.asyncio
async def test_validate_references_success(mock_db):

        mock_db.get.return_value = object()

        await validate_references(
            db=mock_db,
            brand_id=1,
            car_model_id=2,
            country_id=3,
            region_id=4,
            city_id=5
        )

        assert mock_db.get.call_count == 5


@pytest.mark.asyncio
async def test_validate_references_brand_not_found(mock_db):
    mock_db.get.side_effect = [None]

    with pytest.raises(HTTPException) as exc_info:
        await validate_references(mock_db, 1, 2, 3, 4, 5)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Brand does not exist"


@pytest.mark.asyncio
async def test_validate_references_city_not_found(mock_db):
    mock_db.get.side_effect = [
        object(),
        object(),
        object(),
        object(),
        None
    ]

    with pytest.raises(HTTPException) as exc_info:
        await validate_references(mock_db, 1, 2, 3, 4, 5)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "City does not exist"


@pytest.mark.asyncio
async def test_check_profanity_attempts_success():
    mock_client = AsyncMock()
    mock_client.get.return_value = "0"
    mock_client.incr.return_value = 1
    mock_client.expire.return_value = True

    with patch.object(redis_client, "client", mock_client):
        result = await check_profanity_attempts("some_key")

    assert result is True
    mock_client.get.assert_called_once_with("some_key")
    mock_client.incr.assert_called_once_with("some_key")
    (mock_client.expire.assert_called_once_with("some_key", 24 * 60 * 60))


@pytest.mark.asyncio
async def test_check_profanity_attempts_failure():
    mock_client = AsyncMock()
    mock_client.get.return_value = "2"

    with patch.object(redis_client, "client", mock_client):
        result = await check_profanity_attempts("some_key")

    assert result is False
    mock_client.get.assert_called_once_with("some_key")


@pytest.mark.asyncio
async def test_create_listing_service_success(mock_db, sub_factory):
    listing_data = sub_factory('listing_schema_to_create_good_listing')
    user_id = 1
    images = []

    mock_redis_client = AsyncMock()
    mock_redis_client.delete.return_value = None

    with patch('app.services.listing.profanity_filter', result_value=True) as mock_profanity_filter:
        with patch.object(redis_client, "client", mock_redis_client):

            result = await create_listing_service(mock_db, listing_data, user_id, images)

    assert result.user_id == listing_data.user_id
    assert result.title == listing_data.title
    assert result.description == listing_data.description
    assert result.is_active is True

    mock_profanity_filter.assert_awaited_once()
    mock_redis_client.delete.assert_awaited_once_with(f"profanity_attempts:user:{user_id}")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_listing_service_failure(mock_db, sub_factory):
    listing_data = sub_factory('listing_schema_to_create_good_listing')
    with patch('app.services.listing.profanity_filter', return_value=False) as mock_profanity_filter:
        with patch('app.services.listing.check_profanity_attempts', return_value=True) as mock_check_profanity_attempts:
            with pytest.raises(HTTPException) as exc_info:
                await create_listing_service(mock_db, listing_data, 1, [])

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Profanity check failed"
    mock_profanity_filter.assert_awaited_once()
    mock_check_profanity_attempts.assert_called_once()


@pytest.mark.asyncio
async def test_user_manager_true_cases(listing_user_factory, mock_db):
    admin = listing_user_factory("test_admin_user")
    manager = listing_user_factory("test_manager_user")
    user = listing_user_factory("test_base_user")

    # Superadmin → base_user
    assert await user_manager(performer=admin, target=user, db=mock_db, task="any") is True

    # Admin → manager/user
    assert await user_manager(performer=admin, target=manager, db=mock_db, task="any") is True

    # Manager → user (only for toggle_ban_status)
    assert await user_manager(performer=manager, target=user, db=mock_db, task="toggle_ban_status") is True


@pytest.mark.asyncio
async def test_user_manager_false_and_error_cases(listing_user_factory, mock_db):
    admin = listing_user_factory("test_admin_user")
    manager = listing_user_factory("test_manager_user")
    user = listing_user_factory("test_base_user")

    # Without target user
    with pytest.raises(HTTPException) as exc_info:
        await user_manager(performer=admin, target=None, db=mock_db, task="any")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    # Trying to do something with himself
    with pytest.raises(HTTPException) as exc_info:
        await user_manager(performer=user, target=user, db=mock_db, task="toggle_ban_status")
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    # Manager → Admin
    assert await user_manager(performer=manager, target=admin, db=mock_db, task="toggle_ban_status") is False

    # Admin → Admin for `changing role`
    another_admin = UserModel(
        id=1000,
        auth_user_id=1000,
        email="admin2@example.com",
        username="Admin2",
        is_superadmin=True,
        is_banned=False,
        is_premium=False,
        premium_expires_at=None,
        role_id=1,
    )
    assert await user_manager(performer=admin, target=another_admin, db=mock_db, task="changing role") is False
