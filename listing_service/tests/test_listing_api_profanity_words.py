import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from app.models.profanity_words import ProfanityWords


@pytest.mark.asyncio
async def test_get_profanity_words(client, mock_db, sub_factory):
    words = [
        sub_factory("profanity_word"),
        ProfanityWords(id=1, word="badword")
    ]

    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = words
    result_mock.scalars.return_value = scalars_mock

    mock_db.execute = AsyncMock(return_value=result_mock)

    with patch("app.api.profanity_words.permission_checker", return_value=None):
        response = await client.get("/api-listings/profanity", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == len(words)


@pytest.mark.asyncio
async def test_create_profanity_word_success(client, mock_db, sub_factory):
    word = sub_factory("profanity_word")

    mock_db.scalar = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    async def refresh_side_effect(instance):
        instance.id = word.id
        instance.name = word.word

    mock_db.refresh.side_effect = refresh_side_effect

    with patch("app.api.profanity_words.permission_checker", return_value=None):
        response = await client.post(
            "/api-listings/profanity",
            json={"word": word.word},
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["word"] == word.word
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_profanity_word_success(client, mock_db, sub_factory):
    word = sub_factory("profanity_word")
    mock_db.get = AsyncMock(return_value=word)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    with patch("app.api.profanity_words.permission_checker", return_value=None):
        response = await client.delete(
            f"/api-listings/profanity/{word.id}",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert f"Profanity_word {word.id} deleted" in response.json()["message"]
    mock_db.delete.assert_awaited_once_with(word)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_profanity_word_not_found(client, mock_db):
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.api.profanity_words.permission_checker", return_value=None):
        response = await client.delete(
            "/api-listings/profanity/999",
            headers={"Authorization": "Bearer testtoken"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
