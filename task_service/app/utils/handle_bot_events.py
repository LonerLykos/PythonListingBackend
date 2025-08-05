from app.python_ria_bot import send_violation_notice, send_creating_notice
from shared.utils import constants as rb_const

EVENT_HANDLERS = {
    rb_const.EVENT_ADMIN_NOTIFY: {
        "required_keys": ["title", "description", "listing_id", "user_id"],
        "handler": send_violation_notice,
    },
    rb_const.EVENT_ADMIN_CREATE: {
        "required_keys": [
            "title",
            "country_name_or_id",
            "region_name_or_id",
            "city_name",
            "brand_name_or_id",
            "car_model_name",
            "who_ask_for"
        ],
        "handler": send_creating_notice
    },
}


async def handle_event(event_type: str, data: dict):
    config = EVENT_HANDLERS.get(event_type)
    if not config:
        raise ValueError(f"Unsupported event type: {event_type}")

    required_keys = config["required_keys"]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing keys in event data: {missing_keys}")

    handler = config["handler"]
    await handler(**data)
