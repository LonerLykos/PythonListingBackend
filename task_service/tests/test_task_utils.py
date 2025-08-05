import pytest
from unittest.mock import AsyncMock, MagicMock
from app.utils.additional_check_or_create import (
    get_or_create_country,
    get_or_create_region,
    create_city,
    get_or_create_brand,
    create_carmodel,
)
from app.utils.handle_bot_events import handle_event
from listing_service.app.models import (
    Country as CountryModel,
    Region as RegionModel,
    City as CityModel
)
from listing_service.app.models import Brand as BrandModel, CarModel
from shared.utils import constants as rb_const


@pytest.mark.asyncio
@pytest.mark.parametrize('test_name_or_id, test_data', [
    ('Ukraine', CountryModel(id=1, name="Ukraine")),
    (2, CountryModel(id=2, name="USA"))
])
async def test_get_or_create_country(mock_db, test_name_or_id, test_data):
    if isinstance(test_name_or_id, int):
        mock_db.get = AsyncMock(return_value=test_data)

        result = await get_or_create_country(mock_db, test_name_or_id)

        assert result.name == "USA"
        assert result.id == 2
    else:
        mock_db.add = MagicMock()

        async def flush_side_effect():
            mock_db.add.call_args[0][0].id = test_data.id

        mock_db.flush.side_effect = flush_side_effect

        result = await get_or_create_country(mock_db, test_name_or_id)
        assert result.name == "Ukraine"
        assert result.id == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('test_name_or_id, test_data', [
    ('Lviv', RegionModel(id=1, name="Lviv", country_id=1)),
    (2, RegionModel(id=2, name="Kyiv", country_id=1))
])
async def test_get_or_create_region(mock_db, test_name_or_id, test_data):
    if isinstance(test_name_or_id, int):
        mock_db.get = AsyncMock(return_value=test_data)

        result = await get_or_create_region(mock_db, test_name_or_id, 1)

        assert result.name == "Kyiv"
        assert result.id == 2
    else:
        mock_db.add = MagicMock()

        async def flush_side_effect():
            mock_db.add.call_args[0][0].id = test_data.id

        mock_db.flush.side_effect = flush_side_effect

        result = await get_or_create_region(mock_db, test_name_or_id, 1)
        assert result.name == "Lviv"
        assert result.id == 1


@pytest.mark.asyncio
async def test_create_city(mock_db):
    mock_city = CityModel(id=1, name="Kyiv", region_id=1)
    mock_db.add = MagicMock()

    result = await create_city(mock_db, mock_city.name, mock_city.region_id)

    assert result is None
    assert mock_db.add.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('test_name_or_id, test_data', [
    ('BMW', BrandModel(id=1, name="BMW")),
    (2, BrandModel(id=2, name="Lamborghini"))
])
async def test_get_or_create_brand(mock_db, test_name_or_id, test_data):
    if isinstance(test_name_or_id, int):
        mock_db.get = AsyncMock(return_value=test_data)

        result = await get_or_create_brand(mock_db, test_name_or_id)

        assert result.name == "Lamborghini"
        assert result.id == 2
    else:
        mock_db.add = MagicMock()

        async def flush_side_effect():
            mock_db.add.call_args[0][0].id = test_data.id

        mock_db.flush.side_effect = flush_side_effect

        result = await get_or_create_brand(mock_db, test_name_or_id)
        assert result.name == "BMW"
        assert result.id == 1


@pytest.mark.asyncio
async def test_create_carmodel(mock_db):
    mock_car = CarModel(id=1, name="Kyiv", brand_id=1)
    mock_db.add = MagicMock()

    result = await create_carmodel(mock_db, mock_car.name, mock_car.brand_id)

    assert result is None
    assert mock_db.add.call_count == 1


@pytest.mark.asyncio
async def test_handle_event_missing_keys():
    data = {
        "description": "Test desc",
        "listing_id": 1,
        "user_id": 42
    }
    with pytest.raises(ValueError) as excinfo:
        await handle_event(rb_const.EVENT_ADMIN_NOTIFY, data)
    assert "Missing keys" in str(excinfo.value)


@pytest.mark.asyncio
async def test_handle_event_unsupported_event():
    data = {}
    with pytest.raises(ValueError) as excinfo:
        await handle_event("unsupported_event", data)
    assert "Unsupported event type" in str(excinfo.value)
