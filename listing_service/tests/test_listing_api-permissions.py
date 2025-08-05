import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.models.user import Permission as PermissionModel


@pytest.mark.asyncio
async def test_get_all_permissions(client, mock_db):
    permissions = [
        PermissionModel(id=1, name="view_users", description="Can view users"),
        PermissionModel(id=2, name="view_dealerships", description="Can view dealerships"),
    ]

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = permissions
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.get("/api-listings/permissions", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == status.HTTP_200_OK
    json_resp = response.json()
    assert len(json_resp) == len(permissions)


@pytest.mark.asyncio
async def test_create_permission_success(client, mock_db, sub_factory):
    permission_mock = sub_factory("permission")

    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = permission_mock.id
        instance.name = permission_mock.name
        instance.description = permission_mock.description

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/permissions",
            json={"name": permission_mock.name, "description": permission_mock.description},
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == permission_mock.name
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_permission_conflict(client, mock_db, sub_factory):
    permission = sub_factory("permission")
    mock_db.scalar = AsyncMock(return_value=permission)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/permissions",
            json={"name": permission.name, "description": "Whatever"},
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_get_permission_by_id_success(client, mock_db, sub_factory):
    permission = sub_factory("permission")
    mock_db.get = AsyncMock(return_value=permission)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.get(
            f"/api-listings/permissions/{permission.id}",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == permission.name


@pytest.mark.asyncio
async def test_get_permission_by_id_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.get(
            "/api-listings/permissions/9999",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_permission_success(client, mock_db, sub_factory):
    permission = sub_factory("permission")
    mock_db.get = AsyncMock(return_value=permission)
    mock_db.commit = AsyncMock()

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.put(
            f"/api-listings/permissions/{permission.id}",
            json={"name": "updated_name", "description": "Updated description"},
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "updated_name"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_permission_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.put(
            "/api-listings/permissions/9999",
            json={"name": "some_name"},
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_permission_success(client, mock_db, sub_factory):
    permission = sub_factory("permission")
    mock_db.get = AsyncMock(return_value=permission)
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.delete(
            f"/api-listings/permissions/{permission.id}",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert f"Permission {permission.id} deleted" in response.json()["message"]
    mock_db.commit.assert_awaited_once()
    mock_db.delete.assert_awaited_once_with(permission)


@pytest.mark.asyncio
async def test_delete_permission_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.permissions.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/permissions/9999",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
