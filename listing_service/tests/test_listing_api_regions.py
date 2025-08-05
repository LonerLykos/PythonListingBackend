import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.models import Country


@pytest.mark.asyncio
async def test_get_all_countries(client, mock_db, sub_factory):
    mock_country = sub_factory('country_model')

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [mock_country]
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/location/countries")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_create_country_success(client, mock_db, sub_factory):
    mock_country = sub_factory("country_model")

    mock_user_query_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_user_query_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_user_query_result

    async def refresh_side_effect(instance):
        instance.id = mock_country.id
        instance.name = mock_country.name

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/countries",
            json={"name": mock_country.name},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == mock_country.name
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_country_exist(client, mock_db, sub_factory):
    mock_country = sub_factory('country_model')

    mock_query_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = Country(name=mock_country.name)
    mock_query_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_query_result

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/countries",
            json={"name": mock_country.name},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Country already exists"


@pytest.mark.asyncio
async def test_delete_country_success(client, mock_db, sub_factory):
    mock_country = sub_factory('country_model')
    mock_db.get = AsyncMock(return_value=mock_country)
    mock_db.commit = AsyncMock()

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/countries/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert "deleted" in response.json()["message"]


@pytest.mark.asyncio
async def test_delete_country_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/countries/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Country not found'


@pytest.mark.asyncio
async def test_get_country_with_regions_success(client, mock_db, sub_factory):
    country = sub_factory('country_with_regions')
    mock_db.scalar = AsyncMock(return_value=country)

    response = await client.get("/api-listings/location/country-with-regions/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 1


@pytest.mark.asyncio
async def test_get_country_not_found(client, mock_db):
    mock_db.scalar = AsyncMock(return_value=None)

    response = await client.get("/api-listings/location/country-with-regions/1")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Country not found'


@pytest.mark.asyncio
async def test_get_all_regions(client, mock_db, sub_factory):
    mock_regions = sub_factory('regions_in_country')

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_regions
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/location/regions")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(mock_regions)


@pytest.mark.asyncio
async def test_create_region_success(client, mock_db, sub_factory):
    mock_region = sub_factory('region_model')
    mock_country = sub_factory('country_model')
    mock_db.get = AsyncMock(return_value=mock_country)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = mock_region.id
        instance.name = mock_region.name
        instance.country_id = mock_region.country_id

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/regions",
            json={"name": mock_region.name, "country_id": mock_region.country_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert (response.json()["name"] == mock_region.name)
    mock_db.add.assert_called_once()
    mock_db.refresh.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_region_exist(client, mock_db, sub_factory):
    mock_country = sub_factory('country_with_regions')
    mock_region = sub_factory('region_model')
    mock_db.scalar = AsyncMock(return_value=mock_country)

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/regions",
            json={"name": mock_region.name, "country_id": mock_region.country_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == 'Region already exists'
    mock_db.scalar.assert_called_once()


@pytest.mark.asyncio
async def test_create_region_country_not_found(client, mock_db, sub_factory):
    mock_region = sub_factory('region_model')
    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/regions",
            json={"name": mock_region.name, "country_id": mock_region.country_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Country not found'


@pytest.mark.asyncio
async def test_delete_region_success(client, mock_db, sub_factory):
    mock_region = sub_factory('region_model')
    mock_db.get = AsyncMock(return_value=mock_region)
    mock_db.commit = AsyncMock()

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/regions/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert "deleted" in response.json()["message"]
    mock_db.get.assert_called_once()
    mock_db.delete.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_region_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/regions/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Region not found'


@pytest.mark.asyncio
async def test_get_region_with_cities_success(client, mock_db, sub_factory):
    mock_region_with_cities = sub_factory('region_with_cities')
    mock_db.scalar = AsyncMock(return_value=mock_region_with_cities)

    response = await client.get('/api-listings/location/region-with-cities/1')
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['id'] == 1


@pytest.mark.asyncio
async def test_get_region_with_cities_where_region_not_found(client, mock_db):
    mock_db.scalar = AsyncMock(return_value=None)

    response = await client.get('/api-listings/location/region-with-cities/1')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Region not found'


@pytest.mark.asyncio
async def test_gat_all_cities(client, mock_db, sub_factory):
    mock_cities = sub_factory('cities_in_region')

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_cities
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/location/cities")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(mock_cities)


@pytest.mark.asyncio
async def test_create_city_success(client, mock_db, sub_factory):
    mock_region = sub_factory('region_model')
    mock_city = sub_factory('city_model')
    mock_db.get = AsyncMock(return_value=mock_region)
    mock_db.commit = AsyncMock()

    async def refresh_side_effect(instance):
        instance.id = mock_city.id
        instance.name = mock_city.name
        instance.region_id = mock_city.region_id

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/cities",
            json={"name": mock_city.name, "region_id": mock_city.region_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == mock_city.name
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_city_with_not_found_region(client, mock_db, sub_factory):
    mock_city = sub_factory('city_model')
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/location/cities",
            json={"name": mock_city.name, "region_id": mock_city.region_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'Region not found'
    mock_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_delete_city_success(client, mock_db, sub_factory):
    mock_city = sub_factory('city_model')
    mock_db.get = AsyncMock(return_value=mock_city)
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/cities/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert "deleted" in response.json()["message"]
    mock_db.get.assert_called_once()
    mock_db.delete.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_city_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.regions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/location/cities/1",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == 'City not found'
    mock_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_regions_by_country(client, mock_db, sub_factory):
    mock_country = sub_factory('country_with_regions')
    mock_db.scalar = AsyncMock(return_value=mock_country)

    response = await client.get("/api-listings/location/regions-by-country/1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_cities_by_region(client, mock_db, sub_factory):
    mock_region = sub_factory('region_with_cities')
    mock_db.scalar = AsyncMock(return_value=mock_region)

    response = await client.get("/api-listings/location/cities-by-region/1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2
