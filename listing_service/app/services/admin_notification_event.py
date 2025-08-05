from app.models import Listing as ListingModel
from shared.utils.rabbitmq import publish_event
from shared.utils import constants as rb_const


async def notification_event(listing: ListingModel):
    await publish_event(
        rb_const.RABBITMQ_QUEUE_ADMIN_EVENTS,
        rb_const.EVENT_ADMIN_NOTIFY,
        {
            "title": listing.title,
            "description": listing.description,
            "listing_id": listing.id,
            "user_id": listing.user_id,
        }
    )


async def creating_event(
        additional_type: str,
        country_name_or_id: str | int | None,
        region_name_or_id: str | int | None,
        city_name: str | None,
        brand_name_or_id: str | int | None,
        car_model_name: str | None,
        user_id: int):
    await publish_event(
        rb_const.RABBITMQ_QUEUE_ADMIN_EVENTS,
        rb_const.EVENT_ADMIN_CREATE,
        {
            "title": additional_type,
            "country_name_or_id": country_name_or_id,
            "region_name_or_id": region_name_or_id,
            "city_name": city_name,
            "brand_name_or_id": brand_name_or_id,
            "car_model_name": car_model_name,
            "who_ask_for": user_id,
        }
    )
