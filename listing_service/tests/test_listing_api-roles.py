import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.models.user import Role


@pytest.mark.asyncio
async def test_get_all_roles(client, mock_db, sub_factory):
    mock_roles = [
        sub_factory('role'),
        Role(id=1, name="Admin")
    ]
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_roles
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.get(
            "/api-listings/roles",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(mock_roles)


@pytest.mark.asyncio
async def test_create_role_success(client, mock_db, sub_factory):
    mock_role = sub_factory('role')

    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = mock_role.id
        instance.name = mock_role.name

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/roles",
            json={"name": mock_role.name},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == mock_role.name
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_role_conflict(client, mock_db, sub_factory):
    mock_role = sub_factory('role')
    mock_db.scalar = AsyncMock(return_value=mock_role)

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/roles",
            json={"name": mock_role.name},
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Role already exists"


@pytest.mark.asyncio
async def test_get_role_by_id_success(client, mock_db, sub_factory):
    mock_role = sub_factory('role')
    mock_db.get = AsyncMock(return_value=mock_role)

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.get(
            f"/api-listings/roles/{mock_role.id}",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == mock_role.name
    mock_db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_role_by_id_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.get(
            "/api-listings/roles/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Role not found"
    mock_db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_role_by_id_success(client, mock_db, sub_factory):
    mock_role = sub_factory('role')
    mock_db.get = AsyncMock(return_value=mock_role)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.delete(
            f"/api-listings/roles/{mock_role.id}",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Role 4 deleted"
    mock_db.get.assert_awaited_once()
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_role_by_id_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.roles.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/roles/999",
            headers={"Authorization": "Bearer testtoken"}
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Role not found"
    mock_db.get.assert_awaited_once()
