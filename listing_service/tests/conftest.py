from datetime import datetime, timezone, timedelta, date
from better_profanity import profanity
from fastapi import UploadFile
from io import BytesIO
from PIL import Image
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_listing_db
from app.main import app
from app.models import (
    User as UserModel,
    Role as RoleModel,
    Permission as PermissionModel,
    Listing as ListingModel,
    Country as CountryModel,
    Region as RegionModel,
    City as CityModel,
    ProfanityWords as ProfanityWordsModel,
    Brand as BrandModel,
    CarModel,
    ExchangeRate as ExchangeRateModel,
    RolePermission as RolePermissionPairModel,
)
from app.schemas.listing import ListingCreate as ListingCreateSchema
from app.utils.token_utils import get_user_from_token


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
def override_db_dependency(mock_db):
    async def _override():
        yield mock_db
    app.dependency_overrides[get_listing_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def override_user_dependency(listing_user_factory):
    user = listing_user_factory("test_user_with_permission")
    async def _override():
        return user
    app.dependency_overrides[get_user_from_token] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def listing_user_factory():
    def _create_user(user_type: str):
        if user_type == "test_base_user":
            permission = PermissionModel(id=1, name="manage_listings", description='Create/update/delete listings')

            role = RoleModel(
                id=3,
                name="user",
                permissions=[permission],
            )

            return UserModel(
                id=1,
                auth_user_id=1,
                email="test1@example.com",
                username="Test1",
                is_superadmin=False,
                is_banned=False,
                is_premium=False,
                premium_expires_at=None,
                role_id=3,
                role=role
            )

        elif user_type == "test_base_premium_user":
            return UserModel(
                id=2,
                auth_user_id=2,
                email="test2@example.com",
                username="Test2",
                is_superadmin=False,
                is_banned=False,
                is_premium=True,
                premium_expires_at=date.today() + timedelta(days=1),
                role_id=3,
            )

        elif user_type == "test_manager_user":
            return UserModel(
                id=3,
                auth_user_id=3,
                email="test3@example.com",
                username="Test3",
                is_superadmin=False,
                is_banned=False,
                is_premium=True,
                premium_expires_at=date.today() + timedelta(days=1),
                role_id=2,
            )

        elif user_type == "test_admin_user":
            return UserModel(
                id=4,
                auth_user_id=4,
                email="test4@example.com",
                username="Test4",
                is_superadmin=True,
                is_banned=False,
                is_premium=True,
                premium_expires_at=date.today() + timedelta(days=1),
                role_id=1,
            )

        elif user_type == "test_banned_user":
            return UserModel(
                id=5,
                auth_user_id=5,
                email="test5@example.com",
                username="Test5",
                is_superadmin=False,
                is_banned=True,
                is_premium=False,
                premium_expires_at=None,
                role_id=3,
            )

        elif user_type == "test_user_with_permission":
            permission1 = PermissionModel(id=1, name="moderate_listings", description="Can moderate listings")
            permission2 = PermissionModel(id=2, name="edit_profile", description="Can edit profile")

            role = RoleModel(
                id=1,
                name="admin",
                permissions=[permission1, permission2],
            )

            user = UserModel(
                id=6,
                auth_user_id=6,
                email="test6@example.com",
                username="Test6",
                is_superadmin=False,
                is_banned=False,
                is_premium=True,
                premium_expires_at=date(2099, 1, 1),
                role_id=role.id,
                role=role,
            )
            return user

        else:
            return None
    return _create_user


@pytest.fixture
def sub_factory():
    def _create_sub_info(info_type: str):
        if info_type == "brand":
            return BrandModel(id=1, name='BMW')

        elif info_type == "brand_with_car_models":
            car_models = [
                CarModel(id=1, name='X5', brand_id=1),
                CarModel(id=2, name='X6', brand_id=1)
            ]

            return BrandModel(id=1, name='BMW', car_models=car_models)

        elif info_type == "car_model":
            return CarModel(id=1, name='X5', brand_id=1)

        elif info_type == "car_models_in_brand":
            return [
                CarModel(id=1, name='X5', brand_id=1),
                CarModel(id=2, name='X6', brand_id=1)
            ]

        elif info_type == 'country_model':
            return CountryModel(id=1, name='Ukraine')

        elif info_type == "country_with_regions":
            regions = [
                RegionModel(id=1, name='Lvivska', country_id=1),
                RegionModel(id=2, name='Kyivska', country_id=1),
            ]
            return CountryModel(id=1, name='Ukraine', regions=regions)

        elif info_type == "region_model":
            return RegionModel(id=1, name='Lvivska', country_id=1)

        elif info_type == "regions_in_country":
            return [
                RegionModel(id=1, name='Lvivska', country_id=1),
                RegionModel(id=2, name='Kyivska', country_id=1),
            ]

        elif info_type == "region_with_cities":
            cities = [
                CityModel(id=1, name='Lviv', region_id=1),
                CityModel(id=2, name='Gorodok', region_id=1),
            ]
            return RegionModel(id=1, name='Lviv', country_id=1, cities=cities)

        elif info_type == "city_model":
            return CityModel(id=1, name='Lviv', region_id=1)

        elif info_type == "cities_in_region":
            return [
                CityModel(id=1, name='Lviv', region_id=1),
                CityModel(id=2, name='Gorodok', region_id=1),
            ]

        elif info_type == "listing_schema_to_create_good_listing":
            return ListingCreateSchema(
                user_id=6,
                brand_id=1,
                car_model_id=1,
                country_id=1,
                region_id=1,
                city_id=1,
                original_price=5000,
                original_currency="UAH",
                title='Test',
                description='Some test description',
                image_urls=[],
                dealership_id=None,
                price_uah=5000.0
            )

        elif info_type == "test_listing":
            return ListingModel(
                id=1,
                user_id=2,
                brand_id=1,
                car_model_id=1,
                country_id=1,
                region_id=1,
                city_id=1,
                original_price=5000,
                original_currency='UAH',
                price_uah=5000.0,
                image_urls=[],
                title='Test',
                description='Some test description',
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                dealership_id=None,
            )

        elif info_type == "test_inactive_listing":
            return ListingModel(
                id=1,
                user_id=2,
                brand_id=1,
                car_model_id=1,
                country_id=1,
                region_id=1,
                city_id=1,
                original_price=5000,
                original_currency='UAH',
                price_uah=5000.0,
                image_urls=[],
                title='Test',
                description='Some test description',
                is_active=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                dealership_id=None,
            )

        elif info_type == "permission":
            return PermissionModel(
                id=1,
                name="Test_permission",
                description="Test description",
            )

        elif info_type == "role":
            return RoleModel(id=4, name="Test_role")

        elif info_type == "profanity_word":
            return ProfanityWordsModel(id=1, word='Test_badword')

        elif info_type == "role_permission_pair":
            return RolePermissionPairModel(id=1, role_id=1, permission_id=1)

        else:
            return None

    return _create_sub_info


@pytest.fixture
def mock_upload_file_jpg():
    image = Image.new("RGB", (1500, 1000), color="red")
    img_bytes = BytesIO()
    image.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    file = UploadFile(filename="test_image.jpg", file=img_bytes)
    return file


@pytest.fixture
def mock_censor_words():
    original = [str(w) for w in profanity.CENSOR_WORDSET]
    profanity.CENSOR_WORDSET.clear()
    yield profanity.CENSOR_WORDSET
    profanity.CENSOR_WORDSET.clear()
    profanity.CENSOR_WORDSET.extend(original)


@pytest.fixture
def mock_exchange_rate():
    return ExchangeRateModel(
        created_at=date.today(),
        sell_usd=40.0,
        sell_eur=44.0
    )
