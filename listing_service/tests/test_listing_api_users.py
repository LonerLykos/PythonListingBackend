import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta, datetime
from fastapi import status
from app.models import User, Role
from tests.conftest import listing_user_factory


@pytest.mark.asyncio
async def test_get_all_users_admin_access(client, mock_db, listing_user_factory):
    users_list = [
        listing_user_factory('test_base_user'),
        listing_user_factory('test_base_premium_user'),
    ]

    mock_result = MagicMock()
    mock_scalar = MagicMock()
    mock_scalar.all.return_value = users_list
    mock_result.scalar.return_value = mock_scalar

    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.get("/api-listings/users", headers={"Authorization": "Bearer token"})

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_all_users_forbidden(client, mock_db):

    response = await client.get("/api-listings/users", headers={"Authorization": "Bearer token"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_become_premium_user(client, mock_db):
    mock_db.commit = AsyncMock()

    async def refresh_side_effect(instance):
        instance.is_premium = True
        instance.premium_expires_at = date.today() + timedelta(days=30)

    mock_db.refresh.side_effect = AsyncMock(side_effect=refresh_side_effect)

    response = await client.patch("/api-listings/users/premium", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["is_premium"] is True
    assert datetime.fromisoformat(response.json()["premium_expires_at"]).date() == date.today() + timedelta(days=30)
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_me(client):

    response = await client.get("/api-listings/users/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["email"] == 'test6@example.com'


@pytest.mark.asyncio
async def test_get_user_by_id_success(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory("test_base_user")
    mock_db.get = AsyncMock(return_value=mock_user)

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.get(f"/api-listings/users/{mock_user.id}", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["email"] == mock_user.email


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(client, mock_db, listing_user_factory):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.get("/api-listings/users/99", headers={"Authorization": "Bearer token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_banned_user_by_id_success(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory("test_base_user")

    mock_db.get = AsyncMock(return_value=mock_user)
    mock_db.commit = AsyncMock()

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.patch(f"/api-listings/users/{mock_user.id}/banned", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["is_banned"] is True


@pytest.mark.asyncio
async def test_banned_user_by_access_denied(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory("test_user_with_permission")
    mock_db.get = AsyncMock(return_value=mock_user)

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.patch(f"/api-listings/users/{mock_user.id}/banned", headers={"Authorization": "Bearer token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_change_user_role_success(client, mock_db, listing_user_factory, sub_factory):
    mock_user = listing_user_factory('test_base_user')
    mock_role = sub_factory('role')

    async def get_side_effect(model, id_):
        if model == User and id_ == mock_user.id:
            return mock_user
        if model == Role and id_ == mock_role.id:
            return mock_role
        return None

    mock_db.get = AsyncMock(side_effect=get_side_effect)

    mock_db.commit = AsyncMock()

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.patch(
            f"/api-listings/users/{mock_user.id}/change-role?role_id=3",
            headers={"Authorization": "Bearer token"},
            json={"role_id": mock_role.id}
        )

    assert response.status_code == 200
    assert response.json()["role_id"] == mock_role.id


@pytest.mark.asyncio
async def test_change_user_role_user_access_denied(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory('test_user_with_permission')
    mock_db.get = AsyncMock(return_value=mock_user)

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.patch(
            f"/api-listings/users/{mock_user.id}/change-role?role_id=3",
            headers={"Authorization": "Bearer token"},
            json={"role_id": 2}
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_change_user_role_role_not_found(client, mock_db, listing_user_factory):
    mock_user = listing_user_factory('test_base_user')

    async def get_side_effect(model, id_):
        if model == User and id_ == mock_user.id:
            return mock_user
        if model == Role and id_ == 999:
            return None
        return None

    mock_db.get = AsyncMock(side_effect=get_side_effect)

    mock_db.commit = AsyncMock()

    with patch("app.api.users.permission_checker", return_value=None):
        response = await client.patch(
            f"/api-listings/users/{mock_user.id}/change-role?role_id=3",
            headers={"Authorization": "Bearer token"},
            json={"role_id": 999}
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"
