import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_register_user_success(client, mock_db, user_factory):
    with patch("app.api.auth.create_user", AsyncMock(
            return_value=user_factory('test_inactive_user'))) as mock_create_user:
        with patch("app.api.auth.create_email_verify_token", AsyncMock(return_value="verify_token")) as mock_token:
            with patch("app.api.auth.rabbitmq.publish_event", AsyncMock()) as mock_publish:
                response = await client.post(
                    "/api-auth/register",
                    json={"email": "test@example.com", "password": "Te7sP@ss", "username": "Testuser"}
                )
                assert response.status_code == 200
                assert response.json() == {"message": "Please check your email to verify your account"}
                mock_create_user.assert_awaited_once()
                mock_token.assert_awaited_once()
                mock_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_success(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    with patch("app.api.auth.verify_email", AsyncMock(return_value=mock_user)) as mock_verify:
        with patch("app.api.auth.rabbitmq.publish_event", AsyncMock()):
            response = await client.post(
                "/api-auth/verify-email",
                headers={"Authorization": "Bearer verify_token"}
            )
            assert response.status_code == 201
            assert response.json() == {'message': 'You have been verified. Login to continue.'}
            mock_verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_success(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    with patch("app.api.auth.authenticate_user", AsyncMock(return_value=mock_user)) as mock_auth:
        with patch("app.api.auth.create_token_pair",
                   AsyncMock(return_value=("access_token", "refresh_token"))) as mock_tokens:
            response = await client.post(
                "/api-auth/login",
                json={"email": "test@example.com", "password": "Te7sP@ss"}
            )
            assert response.status_code == 200
            assert response.json() == {"access_token": "access_token", "refresh_token": "refresh_token"}
            mock_auth.assert_awaited_once()
            mock_tokens.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, mock_db):
    with patch("app.api.auth.authenticate_user", AsyncMock(return_value=None)):
        response = await client.post(
            "/api-auth/login",
            json={"email": "test@example.com", "password": "wrong_password"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    with patch("app.api.auth.validate_refresh_token",
               AsyncMock(return_value=(mock_user, "new_access_token", "new_refresh_token"))):
        response = await client.post(
            "/api-auth/refresh",
            headers={"Authorization": "Bearer old_refresh_token"}
        )
        assert response.status_code == 200
        assert response.json() == {"access_token": "new_access_token", "refresh_token": "new_refresh_token"}


@pytest.mark.asyncio
async def test_get_users_success(client, mock_db, user_factory):
    mock_user = user_factory('test_admin_user')
    mock_users = [
        user_factory('test_active_user'),
        user_factory('test_inactive_user')]

    with patch("app.api.auth.get_current_user", AsyncMock(return_value=mock_user)):

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_users

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db.execute.return_value = mock_result

        response = await client.get(
            "/api-auth/users",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["email"] == "test2@example.com"


@pytest.mark.asyncio
async def test_get_users_failure(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    with patch("app.api.auth.get_current_user", AsyncMock(return_value=mock_user)):
        response = await client.get(
            "/api-auth/users",
            headers={"Authorization": "Bearer user_token"}
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}


@pytest.mark.asyncio
async def test_restore_request_success(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    mock_db.scalar.return_value = mock_user

    with patch("app.api.auth.create_email_verify_token", AsyncMock(return_value="restore_token")) as mock_token:
        with patch("app.api.auth.rabbitmq.publish_event", AsyncMock()) as mock_publish:
            response = await client.post(
                "/api-auth/restore-request",
                json={"email": "test@example.com"}
            )
            assert response.status_code == 200
            assert response.json() == {"message": f"We send message on test@example.com to restore your password"}
            mock_token.assert_awaited_once()
            mock_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_request_no_user(client, mock_db):
    mock_db.scalar.return_value = None
    response = await client.post(
        "/api-auth/restore-request",
        json={"email": "nonexistent@example.com"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": f"We send message on nonexistent@example.com to restore your password"}


@pytest.mark.asyncio
async def test_restore_password_success(client, mock_db, user_factory):
    mock_user = user_factory('test_active_user')

    with patch("app.api.auth.verify_email", AsyncMock(return_value=mock_user)) as mock_verify:
        with patch("app.api.auth.hashing_password", AsyncMock(return_value="hashed_new_password")) as mock_hash:
            response = await client.patch(
                "/api-auth/restore-password",
                json={"new_password": "new_Te7sP@ss"},
                headers={"Authorization": "Bearer restore_token"}
            )
            assert response.status_code == 200
            assert response.json() == {"message": "Password restored, login to continue"}
            mock_verify.assert_awaited_once()
            mock_hash.assert_awaited_once_with("new_Te7sP@ss")
            mock_db.commit.assert_awaited_once()
