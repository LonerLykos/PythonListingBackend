from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_get_brands_success(client, mock_db, sub_factory):
    brand = sub_factory("brand")

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [brand]
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/cars/brands")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{"id": brand.id, "name": brand.name}]


@pytest.mark.asyncio
async def test_create_brand_success(client, mock_db):
    brand_mock = SimpleNamespace(id=1, name="NewBrand")

    mock_db.scalar.return_value = None
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = brand_mock.id
        instance.name = brand_mock.name

    mock_db.refresh.side_effect = refresh_side_effect

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/cars/brands",
            json={"name": "NewBrand"},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "NewBrand"


@pytest.mark.asyncio
async def test_create_brand_conflict(client, mock_db, sub_factory):
    brand = sub_factory("brand")
    mock_db.scalar.return_value = brand

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/cars/brands",
            json={"name": brand.name},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Brand already exists"


@pytest.mark.asyncio
async def test_delete_brand_success(client, mock_db, sub_factory):
    brand = sub_factory("brand")
    mock_db.get.return_value = brand
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.delete(
        f"/api-listings/cars/brands/{brand.id}",
        headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Brand {brand.id} deleted"}
    mock_db.delete.assert_awaited_once_with(brand)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_brand_not_found(client, mock_db):
    mock_db.get.return_value = None

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.delete(
            f"/api-listings/cars/brands/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Brand not found"


@pytest.mark.asyncio
async def test_get_brand_with_models_success(client, mock_db, sub_factory):
    brand = sub_factory("brand_with_car_models")
    mock_db.scalar.return_value = brand

    response = await client.get(f"/api-listings/cars/brand-with-models/{brand.id}")

    assert response.status_code == status.HTTP_200_OK
    json_resp = response.json()
    assert json_resp["id"] == brand.id
    assert json_resp["name"] == brand.name
    assert len(json_resp["car_models"]) == len(brand.car_models)


@pytest.mark.asyncio
async def test_get_all_models_success(client, mock_db, sub_factory):
    models = sub_factory("car_models_in_brand")

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = models
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    response = await client.get("/api-listings/cars/models")

    assert response.status_code == status.HTTP_200_OK
    json_resp = response.json()
    assert len(json_resp) == len(models)


@pytest.mark.asyncio
async def test_create_model_success(client, mock_db, sub_factory):
    brand = sub_factory("brand")
    brand.car_models = []
    mock_db.scalar.return_value = brand
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    model_data = {"name": "NewModel", "brand_id": brand.id}

    async def refresh_side_effect(instance):
        instance.id = 1
        instance.name = model_data["name"]
        instance.brand_id = brand.id

    mock_db.refresh.side_effect = refresh_side_effect

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/cars/models",
            json=model_data,
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == model_data["name"]
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_model_duplicate(client, mock_db, sub_factory):
    existing_model = sub_factory("car_model")
    brand = sub_factory("brand")
    brand.car_models = [existing_model]

    mock_db.scalar.return_value = brand

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/cars/models",
            json={"name": existing_model.name, "brand_id": brand.id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Model with this name already exists for the brand"


@pytest.mark.asyncio
async def test_create_model_brand_not_found(client, mock_db):
    mock_db.scalar.return_value = None

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/cars/models",
            json={"name": "AnyModel", "brand_id": 999},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Brand not found"


@pytest.mark.asyncio
async def test_delete_model_success(client, mock_db, sub_factory):
    model = sub_factory("car_model")
    mock_db.get.return_value = model
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.delete(
            f"/api-listings/cars/models/{model.id}",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Model {model.id} deleted"}
    mock_db.delete.assert_awaited_once_with(model)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_model_not_found(client, mock_db):
    mock_db.get.return_value = None

    with patch('app.api.cars.permission_checker', return_value=None):
        response = await client.delete(
            "/api-listings/cars/models/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Model not found"


@pytest.mark.asyncio
async def test_get_models_by_brand_success(client, mock_db, sub_factory):
    brand = sub_factory("brand")
    models = sub_factory("car_models_in_brand")
    brand.car_models = models

    mock_db.scalar.return_value = brand

    response = await client.get(f"/api-listings/cars/models-by-brand/{brand.id}")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(models)


@pytest.mark.asyncio
async def test_get_models_by_brand_not_found(client, mock_db):
    mock_db.scalar.return_value = None

    response = await client.get("/api-listings/cars/models-by-brand/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Brand not found"
