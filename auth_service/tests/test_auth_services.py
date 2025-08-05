from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status
from jose import JWTError, ExpiredSignatureError, jwt
from app.core.config import settings
from app.services.auth import (
    create_user,
    authenticate_user,
    pwd_context,
    get_user_by_id,
    decode_token,
    create_tokens,
    get_current_user,
    token_to_blacklist,
    token_checker,
    verify_email,
    validate_refresh_token
)
from app.models.auth import User, TokenType, ActiveToken, BlacklistedToken


@pytest.mark.asyncio
async def test_create_user_success(mock_db, user_factory):
    mock_user_query_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    mock_user_query_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_user_query_result

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    user_data = user_factory('schema_user')

    with patch("app.services.auth.hashing_password", new_callable=AsyncMock, return_value="hashed_password"):
        user = await create_user(mock_db, user_data.email, user_data.password, user_data.username)

    assert user.email == "test@example.com"
    assert user.username == "Testuser"
    assert user.is_active is False

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_email_exists(mock_db, user_factory):
    mock_user_query_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = User(email="test@example.com")
    mock_user_query_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_user_query_result

    user_data = user_factory('schema_user')
    with pytest.raises(HTTPException) as exc:
        await create_user(mock_db, user_data.email, user_data.password, user_data.username)
    assert exc.value.status_code == 400
    assert "Email already registered" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    mock_user_base_password = mock_user.password_hash
    mock_user.password_hash = pwd_context.hash(mock_user.password_hash)
    mock_db.scalar.return_value = mock_user

    result = await authenticate_user(mock_db, mock_user.email, mock_user_base_password)

    assert result == mock_user
    mock_db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_user_failures(mock_db, user_factory):
    # If user is None
    mock_user = None
    mock_db.scalar.return_value = mock_user

    result = await authenticate_user(mock_db, 'test@email.com', 'some_pass')

    assert result is None

    # If user not active
    mock_user2 = user_factory('test_inactive_user')
    mock_user2_base_password = mock_user2.password_hash
    mock_user2.password_hash = pwd_context.hash(mock_user2.password_hash)

    result2 = await authenticate_user(mock_db, mock_user2.email, mock_user2_base_password)

    assert result2 is None

    # If user_pass isn't verify
    mock_user3 = user_factory('test_active_user')
    mock_user3_base_password = 'some_invalid_password'
    mock_user3.password_hash = pwd_context.hash(mock_user3.password_hash)

    result3 = await authenticate_user(mock_db, mock_user3.email, mock_user3_base_password)

    assert result3 is None


@pytest.mark.asyncio
async def test_get_user_by_id_is_none(mock_db):
    mock_user = None
    mock_db.scalar.return_value = mock_user

    result = await get_user_by_id(mock_db, 1)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id(mock_db, user_factory):
    mock_user = user_factory('test_active_user')
    mock_db.scalar.return_value = mock_user

    result = await get_user_by_id(mock_db, mock_user.id)
    assert result == mock_user


@pytest.mark.asyncio
async def test_decode_token_success():
    token = "valid_token"
    secret = "secret"
    algo = "HS256"

    with patch("app.services.auth.jwt.decode", return_value={"sub": "123"}):
        user_id = await decode_token(token, secret, algo)
        assert user_id == 123


@pytest.mark.asyncio
async def test_decode_token_missing_sub():
    token = "no_sub_token"
    secret = "secret"
    algo = "HS256"

    with patch("app.services.auth.jwt.decode", return_value={}):
        with pytest.raises(HTTPException) as exc:
            await decode_token(token, secret, algo)
        assert exc.value.status_code == 401
        assert "You need to be logged" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_decode_token_expired():
    token = "expired_token"
    secret = "secret"
    algo = "HS256"

    with patch("app.services.auth.jwt.decode", side_effect=ExpiredSignatureError()):
        with pytest.raises(HTTPException) as exc:
            await decode_token(token, secret, algo)
        assert exc.value.status_code == 401
        assert "expired" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_decode_token_invalid():
    token = "invalid_token"
    secret = "secret"
    algo = "HS256"

    with patch("app.services.auth.jwt.decode", side_effect=JWTError("Invalid")):
        with pytest.raises(HTTPException) as exc:
            await decode_token(token, secret, algo)
        assert exc.value.status_code == 401
        assert "logged" in str(exc.value.detail).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "token_type,secret_key,duration",
    [
        (TokenType.AUTH_ACCESS, settings.access_token_secret_key, settings.access_token_expire_hours),
        (TokenType.AUTH_REFRESH, settings.refresh_token_secret_key, settings.refresh_token_expire_days),
        (TokenType.EMAIL_VERIFY, settings.email_verify_secret_key, settings.email_verify_expire_hours),
    ]
)
async def test_create_tokens_all_types(token_type, secret_key, duration, mock_db):
    email = "test@example.com"
    user_id = 42
    expire_at = duration

    token = await create_tokens(token_type, expire_at, email, user_id, mock_db)

    assert isinstance(token, str)

    decoded = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
    assert decoded["sub"] == str(user_id)
    assert decoded["email"] == email

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_success(mock_db, user_factory):
    mock_token = "mock_token"
    mock_user = user_factory('test_active_user')

    with patch("app.services.auth.token_checker", return_value=None) as mock_checker:
        with patch("app.services.auth.decode_token", return_value=2) as mock_decoder:
            with patch("app.services.auth.get_user_by_id", return_value=mock_user) as mock_get_user:

                result = await get_current_user(mock_token, mock_db)
                assert result == mock_user

                args, kwargs = mock_checker.call_args

                assert args[0] == mock_db
                assert args[1] == mock_token
                assert isinstance(args[2], HTTPException)
                assert args[2].status_code == 401
                assert args[2].detail == "Could not validate credentials"
                assert args[3] == TokenType.AUTH_ACCESS

                mock_decoder.assert_called_once_with(
                    mock_token,
                    settings.access_token_secret_key,
                    settings.algorithm
                )

                mock_get_user.assert_called_once_with(mock_db, mock_user.id)


@pytest.mark.asyncio
async def test_token_to_blacklist(mock_db):
    token = ActiveToken(token="test-token")

    await token_to_blacklist(mock_db, token)

    added_token = mock_db.add.call_args[0][0]
    assert isinstance(added_token, BlacklistedToken)
    assert added_token.token == "test-token"

    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_checker_success(mock_db, token_factory):
    credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    mock_db_token = token_factory('access')

    mock_db.scalar = AsyncMock(side_effect=[None, mock_db_token])

    result = await token_checker(mock_db, mock_db_token.token, credentials, mock_db_token.token_type)

    assert result == mock_db_token
    assert mock_db.scalar.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blacklisted_token,mock_db_token",
    [
        (True, None),
        (None, None, ),
        (None, ActiveToken(
            id=1,
            token_type=TokenType.AUTH_ACCESS,
            token="test-token",
            user_id=1,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )),
    ]
)
async def test_token_checker_failure(mock_db, blacklisted_token, mock_db_token):
    token = "test-token"
    credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    token_type = TokenType.AUTH_ACCESS

    mock_db.scalar = AsyncMock(side_effect=[blacklisted_token, mock_db_token])
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()

    with patch("app.services.auth.token_to_blacklist", new_callable=AsyncMock):
        with pytest.raises(HTTPException) as exc:
            await token_checker(mock_db, token, credentials, token_type)

        assert exc.value.status_code == 401
        assert "Could not validate credentials" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_verify_email_create_user(mock_db, user_factory, token_factory):
    mock_user = user_factory('test_inactive_user')
    mock_db_token = token_factory('verify')
    with patch("app.services.auth.token_checker", return_value=mock_db_token) as mock_checker:
        with patch("app.services.auth.decode_token", return_value=1) as mock_decoder:
            with patch("app.services.auth.publish_event", return_value=None) as mock_publish_event:

                mock_db.scalar = AsyncMock(return_value=mock_user)
                result = await verify_email(mock_db, mock_db_token.token, 'create_user')
                assert result == mock_user

                args, kwargs = mock_checker.call_args

                assert args[0] == mock_db
                assert args[1] == mock_db_token.token
                assert isinstance(args[2], HTTPException)
                assert args[2].status_code == 401
                assert args[2].detail == "You need register again."
                assert args[3] == TokenType.EMAIL_VERIFY

                mock_decoder.assert_called_once_with(
                    mock_db_token.token,
                    settings.email_verify_secret_key,
                    settings.algorithm
                )

                mock_publish_event.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_restore_pass(mock_db, user_factory, token_factory):
    mock_user = user_factory('test_inactive_user')
    mock_db_token = token_factory('verify')
    with patch("app.services.auth.token_checker", return_value=mock_db_token) as mock_checker:
        with patch("app.services.auth.decode_token", return_value=1) as mock_decoder:
                mock_db.scalar = AsyncMock(return_value=mock_user)
                result = await verify_email(mock_db, mock_db_token.token)
                assert result == mock_user

                args, kwargs = mock_checker.call_args

                assert args[0] == mock_db
                assert args[1] == mock_db_token.token
                assert isinstance(args[2], HTTPException)
                assert args[2].status_code == 401
                assert args[2].detail == "You need register again."
                assert args[3] == TokenType.EMAIL_VERIFY

                mock_decoder.assert_called_once_with(
                    mock_db_token.token,
                    settings.email_verify_secret_key,
                    settings.algorithm
                )


@pytest.mark.asyncio
async def test_validate_refresh_token(mock_db, user_factory, token_factory):
    mock_db_token = token_factory('refresh')
    mock_user = user_factory('test_active_user')
    mock_new_access_token = token_factory('access')
    mock_new_refresh_token = token_factory('refresh')
    with patch("app.services.auth.token_checker", return_value=mock_db_token) as mock_checker:
        with patch("app.services.auth.decode_token", return_value=2) as mock_decoder:
            with patch("app.services.auth.get_user_by_id", return_value=mock_user) as mock_get_user_by_id:
                 with patch("app.services.auth.token_to_blacklist", return_value=None) as mock_token_to_blacklist:
                    with patch("app.services.auth.create_token_pair", return_value=(mock_new_access_token, mock_new_refresh_token)) as mock_create_token_pair:

                        result = await validate_refresh_token(mock_db, mock_db_token.token)
                        assert result == (mock_user, mock_new_access_token, mock_new_refresh_token)

                        args, kwargs = mock_checker.call_args

                        assert args[0] == mock_db
                        assert args[1] == mock_db_token.token
                        assert isinstance(args[2], HTTPException)
                        assert args[2].status_code == 401
                        assert args[2].detail == "Something wrong. Try again or relogin."
                        assert args[3] == TokenType.AUTH_REFRESH

                        mock_decoder.assert_called_once_with(
                            mock_db_token.token,
                            settings.refresh_token_secret_key,
                            settings.algorithm
                        )

                        mock_get_user_by_id.assert_called_once_with(mock_db, mock_decoder.return_value)

                        mock_token_to_blacklist.assert_called_once_with(mock_db, mock_db_token)
                        mock_db.delete.assert_called_once_with(mock_db_token)

                        mock_create_token_pair.assert_called_once_with(mock_db, mock_user)
                        mock_db.commit.assert_called_once()
