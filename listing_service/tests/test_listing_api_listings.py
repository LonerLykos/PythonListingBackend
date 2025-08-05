import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.main import app
from app.models.listing import Listing, Currency
from app.utils.token_utils import get_user_from_token, get_optional_user_from_token
from tests.conftest import listing_user_factory


@pytest.mark.asyncio
async def test_get_all_active_listings_success(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_listing]
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/listings")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_listing_success(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()

    form_data = {
        "brand_id": 1,
        "car_model_id": 1,
        "country_id": 1,
        "region_id": 1,
        "original_price": 5000,
        "original_currency": 'UAH',
        "title": "Test Car",
        "description": "A nice car",
    }

    files = [
        ("images", ("test1.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("images", ("test2.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("images", ("test3.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
    ]

    with patch("app.api.listings.permission_checker", return_value=None):
        with   patch("app.api.listings.validate_references", return_value=None):
            with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
                with patch("app.api.listings.create_listing_service", AsyncMock(return_value=mock_listing)):

                    response = await client.post(
                        "/api-listings/listings",
                        data=form_data,
                        files=files,
                        headers={"Authorization": "Bearer testtoken"}
                    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_create_listing_limit_reached(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory('test_base_user')

    mock_listing = Listing(id=1)
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_listing]
    result_mock.scalars.return_value = scalars_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    app.dependency_overrides[get_user_from_token] = lambda: mock_user

    form_data = {
        "brand_id": 1,
        "car_model_id": 1,
        "country_id": 1,
        "region_id": 1,
        "original_price": 1000,
        "original_currency": 'UAH',
        "title": "Test Car",
        "description": "A nice car"
    }

    with patch("app.api.listings.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/listings",
            data=form_data,
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You need to be a premium user for creating more than 1 listing"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_listing_image_limit_reached(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()

    form_data = {
        "brand_id": 1,
        "car_model_id": 1,
        "country_id": 1,
        "region_id": 1,
        "original_price": 5000,
        "original_currency": 'UAH',
        "title": "Test Car",
        "description": "A nice car",
    }

    files = [
        ("images", ("test1.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("images", ("test2.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("images", ("test3.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
        ("images", ("test4.jpg", io.BytesIO(b"fake image content"), "image/jpeg")),
    ]

    with patch("app.api.listings.permission_checker", return_value=None):
        with   patch("app.api.listings.validate_references", return_value=None):
            with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
                with patch("app.api.listings.create_listing_service", AsyncMock(return_value=mock_listing)):
                    response = await client.post(
                        "/api-listings/listings",
                        data=form_data,
                        files=files,
                        headers={"Authorization": "Bearer testtoken"}
                    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Maximum 3 images allowed"


@pytest.mark.asyncio
async def test_create_listing_image_invalid_format(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()

    form_data = {
        "brand_id": 1,
        "car_model_id": 1,
        "country_id": 1,
        "region_id": 1,
        "original_price": 5000,
        "original_currency": 'UAH',
        "title": "Test Car",
        "description": "A nice car",
    }

    files = [
        ("images", ("test1.iso", io.BytesIO(b"fake image content"), "image/jpeg")),
    ]

    with patch("app.api.listings.permission_checker", return_value=None):
        with   patch("app.api.listings.validate_references", return_value=None):
            with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
                with patch("app.api.listings.create_listing_service", AsyncMock(return_value=mock_listing)):
                    response = await client.post(
                        "/api-listings/listings",
                        data=form_data,
                        files=files,
                        headers={"Authorization": "Bearer testtoken"}
                    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == f"Invalid file format: test1.iso"


@pytest.mark.asyncio
async def test_create_bad_listing_with_profanity_words(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_inactive_listing')
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()

    form_data = {
        "brand_id": 1,
        "car_model_id": 1,
        "country_id": 1,
        "region_id": 1,
        "original_price": 5000,
        "original_currency": 'UAH',
        "title": "Test Car",
        "description": "A nice car",
    }

    files = [
        ("images", ("test1.png", io.BytesIO(b"fake image content"), "image/jpeg")),
    ]

    with patch("app.api.listings.permission_checker", return_value=None):
        with   patch("app.api.listings.validate_references", return_value=None):
            with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
                with patch("app.api.listings.create_listing_service", AsyncMock(return_value=mock_listing)):
                    with patch("app.api.listings.notification_event", AsyncMock(return_value=None)):
                        response = await client.post(
                            "/api-listings/listings",
                            data=form_data,
                            files=files,
                            headers={"Authorization": "Bearer testtoken"}
                        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "Your listing is under moderation"


@pytest.mark.asyncio
async def test_get_all_listings_success(client, mock_db, sub_factory):
    mock_listings = [sub_factory('test_listing'), sub_factory('test_inactive_listing')]

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_listings
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/listings")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_sub_info(client, mock_db):
    mock_request = {
        "type": "add_country",
        "name": "USA"
    }

    mock_db.scalar = AsyncMock(return_value=None)

    with patch('app.api.listings.additional_checker', return_value=None):
        result = await client.post(
            "/api-listings/listings/additional-request",
            json=mock_request)

    assert result.status_code == status.HTTP_201_CREATED
    assert result.json()["message"] == f"Successfully created request for adding new {mock_request['type']}"


@pytest.mark.asyncio
async def test_toggle_listings_status_success(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    response = await client.patch(f"/api-listings/listings/{mock_listing.id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] == False
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_listings_status_not_found(client, mock_db, sub_factory):
    mock_db.get = AsyncMock(return_value=None)

    response = await client.patch(f"/api-listings/listings/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Listing not found"


@pytest.mark.asyncio
async def test_toggle_listings_status_forbidden(client, mock_db, sub_factory, listing_user_factory):
    mock_user = listing_user_factory('test_base_user')

    app.dependency_overrides[get_user_from_token] = lambda: mock_user

    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    response = await client.patch(f"/api-listings/listings/{mock_listing.id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You can't manage this listing"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_listing_by_id_success_premium_or_manager(client, mock_db,listing_user_factory, sub_factory):
    mock_admin = listing_user_factory('test_user_with_permission')

    app.dependency_overrides[get_optional_user_from_token] = lambda: mock_admin

    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    mock_scalar_result = AsyncMock(return_value=100)
    mock_execute_result = AsyncMock()
    mock_execute_result.scalar = MagicMock(return_value=5)

    mock_db.scalar = mock_scalar_result
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    response = await client.get(f"/api-listings/listings/{mock_listing.id}")

    assert response.status_code == 200
    data = response.json()

    assert "viewed" in data
    assert "avg_price_country" in data
    assert "avg_price_region" in data
    assert data["viewed"] == 5

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_listing_by_id_success_base(client, mock_db,listing_user_factory, sub_factory):
    mock_user = listing_user_factory('test_base_user')

    app.dependency_overrides[get_user_from_token] = lambda: mock_user

    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    response = await client.get(f"/api-listings/listings/{mock_listing.id}")

    assert response.status_code == 200
    data = response.json()

    assert "viewed" not in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_listing_by_id_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    app.dependency_overrides[get_optional_user_from_token] = lambda: None

    response = await client.get("/api-listings/listings/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Listing not found"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_listing_success(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
        with patch("app.api.listings.profanity_filter", AsyncMock(return_value=True)):
            response = await client.put(
                f"/api-listings/listings/{mock_listing.id}",
                data={"description": "A nice car"},
                headers={"Authorization": "Bearer testtoken"}
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["description"] == "A nice car"


@pytest.mark.asyncio
async def test_update_listing_not_found(client, mock_db, sub_factory):
    mock_db.get = AsyncMock(return_value=None)

    response = await client.put(
        f"/api-listings/listings/999",
        data={"description": "A nice car"},
        headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Listing not found"


@pytest.mark.asyncio
async def test_update_listing_without_permission(client, mock_db, sub_factory, listing_user_factory):
    mock_user = listing_user_factory('test_base_user')

    app.dependency_overrides[get_user_from_token] = lambda: mock_user

    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    response = await client.put(
        f"/api-listings/listings/{mock_listing.id}",
        data={"description": "A nice car"},
        headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You can't update this listing"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_listing_profanity_fail(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
        with patch("app.api.listings.profanity_filter", AsyncMock(return_value=False)):
            with patch("app.api.listings.check_profanity_attempts", AsyncMock(return_value=True)):
                response = await client.put(
                    f"/api-listings/listings/{mock_listing.id}",
                    data={"description": "A nice car"},
                    headers={"Authorization": "Bearer testtoken"}
                )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Profanity check failed"


@pytest.mark.asyncio
async def test_update_listing_fail_with_moderation(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.api.listings.create_price_uah", AsyncMock(return_value=5000)):
        with patch("app.api.listings.profanity_filter", AsyncMock(return_value=False)):
            with patch("app.api.listings.check_profanity_attempts", AsyncMock(return_value=False)):
                with patch("app.api.listings.notification_event", AsyncMock()):
                    response = await client.put(
                        f"/api-listings/listings/{mock_listing.id}",
                        data={"description": "A nice car"},
                        headers={"Authorization": "Bearer testtoken"}
                    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Your listing is under moderation"


@pytest.mark.asyncio
async def test_delete_listing_success(client, mock_db, sub_factory):
    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    response = await client.delete(
        f"/api-listings/listings/{mock_listing.id}",
        headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Listing 1 deleted"


@pytest.mark.asyncio
async def test_delete_listing_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    response = await client.delete(f"/api-listings/listings/999", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Listing not found"


@pytest.mark.asyncio
async def test_delete_listing_forbidden(client, mock_db, listing_user_factory, sub_factory):
    mock_user = listing_user_factory('test_base_user')

    app.dependency_overrides[get_user_from_token] = lambda: mock_user

    mock_listing = sub_factory('test_listing')
    mock_db.get = AsyncMock(return_value=mock_listing)

    response = await client.delete(
        f"/api-listings/listings/{mock_listing.id}",
        headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You can't delete this listing"

    app.dependency_overrides.clear()

