import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.models.user import RolePermission


@pytest.mark.asyncio
async def test_get_all_role_permissions(client, mock_db, sub_factory):
    mock_role_permissions_pair = [
        sub_factory('role_permission_pair'),
        RolePermission(id=2, role_id=2, permission_id=2)
    ]

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_role_permissions_pair
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.get(
            "/api-listings/role-permissions",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(mock_role_permissions_pair)


@pytest.mark.asyncio
async def test_create_role_permission_success(client, mock_db, sub_factory):
    mock_role_permission_pair = sub_factory('role_permission_pair')

    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = mock_role_permission_pair.id
        instance.role_id = mock_role_permission_pair.role_id
        instance.permission_id = mock_role_permission_pair.permission_id

    mock_db.refresh.side_effect = refresh_side_effect

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.post(
            "/api-listings/role-permissions",
            json={"role_id": mock_role_permission_pair.role_id,
                  "permission_id": mock_role_permission_pair.permission_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["role_id"] == mock_role_permission_pair.role_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_role_permission_conflict(client, mock_db, sub_factory):
    mock_role_permission_pair = sub_factory("role_permission_pair")
    mock_db.scalar = AsyncMock(return_value=mock_role_permission_pair)

    with patch("app.api.role_permissions.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/role-permissions",
            json={"role_id": mock_role_permission_pair.role_id,
                  "permission_id": mock_role_permission_pair.permission_id},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_get_role_permission_success(client, mock_db, sub_factory):
    mock_role_permission_pair = sub_factory('role_permission_pair')
    mock_db.get = AsyncMock(return_value=mock_role_permission_pair)

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.get(
            f"/api-listings/role-permissions/{mock_role_permission_pair.id}",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 1


@pytest.mark.asyncio
async def test_get_role_permission_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.get(
            "/api-listings/role-permissions/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Role_Permission pair not found"


@pytest.mark.asyncio
async def test_delete_role_permission_success(client, mock_db, sub_factory):
    mock_role_permission_pair = sub_factory('role_permission_pair')
    mock_db.get = AsyncMock(return_value=mock_role_permission_pair)
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.delete(
            f"/api-listings/role-permissions/{mock_role_permission_pair.id}",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == f"Role_Permission_Pair {mock_role_permission_pair.id} deleted"
    mock_db.get.assert_called_once()
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_role_permission_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch('app.api.role_permissions.permission_checker', return_value=None):
        response = await client.delete(
            "/api-listings/role-permissions/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Role_Permission pair not found"
