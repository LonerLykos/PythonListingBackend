import asyncio
import uuid
from aiogram.client.default import DefaultBotProperties
from motor.motor_asyncio import AsyncIOMotorClient
from app.schemas.bot_task_data import BotTaskData
from app.config import settings
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

mongo_client = AsyncIOMotorClient(settings.mongo_db_url)
db = mongo_client[settings.mongo_initdb_database]
collection = db['tasks']


async def init_mongo():
    await collection.create_index("created_at", expireAfterSeconds=settings.mongodb_ttl_seconds)


bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def send_violation_notice(title: str, description: str, listing_id: int, user_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Get Task", callback_data=f"get_task:{listing_id}")]
    ])

    text = (
        f"<b>The listing did not pass moderation.</b>\n"
        f"User: <code>{user_id}</code>\n"
        f"Listing ID: <code>{listing_id}</code>\n"
        f"Title: <code>{title}</code>\n"
        f"Description: <code>{description}</code>\n"
        f"Status: <b>Need to check</b>"
    )

    await bot.send_message(chat_id=settings.telegram_group_id, text=text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("get_task:"))
async def handle_get_task(callback: CallbackQuery):
    listing_id = callback.data.split(":")[1]
    new_text = callback.message.html_text.replace(
        "Status: <b>Need to check</b>",
        "Status: <b>In progress</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Checked", callback_data=f"checked:{listing_id}"),
            InlineKeyboardButton(text="Ban", callback_data=f"ban:{listing_id}"),
        ]
    ])
    await callback.message.edit_text(new_text, reply_markup=keyboard)
    await callback.answer("Task taken. Status updated.")


@dp.callback_query(F.data.startswith("checked:"))
async def handle_checked(callback: CallbackQuery):
    listing_id = callback.data.split(":")[1]
    new_text = callback.message.html_text.replace(
        "Status: <b>In progress</b>",
        "Status: <b>Checked</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)

    from app.tasks import manage_listing_from_bot
    manage_listing_from_bot.delay(listing_id=int(listing_id), task="allow_publication")

    await callback.answer("Marked as checked.")


@dp.callback_query(F.data.startswith("ban:"))
async def handle_ban(callback: CallbackQuery):
    listing_id = callback.data.split(":")[1]
    new_text = callback.message.html_text.replace(
        "Status: <b>In progress</b>",
        "Status: <b>Banned</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)

    from app.tasks import manage_listing_from_bot
    manage_listing_from_bot.delay(listing_id=int(listing_id), task="ban")

    await callback.answer("Marked as banned. Task triggered.")


async def send_creating_notice(
        title: str,
        country_name_or_id: str | int |None,
        region_name_or_id: str | int | None,
        city_name: str | None,
        brand_name_or_id: str | int | None,
        car_model_name: str | None,
        who_ask_for: str):
    task_id = str(uuid.uuid4())

    task_data = BotTaskData(
        title=title,
        country_name_or_id=country_name_or_id,
        region_name_or_id=region_name_or_id,
        city_name=city_name,
        brand_name_or_id=brand_name_or_id,
        car_model_name=car_model_name,
        who_ask_for=who_ask_for
    )

    await collection.insert_one({"_id": task_id, **task_data.model_dump()})
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Get in work", callback_data=f"checking_task:{task_id}")],
    ])

    lines = [
        f"<b>{who_ask_for} asking to adding</b>",
        f"Task: <code>{title}</code>",
        "Additional sending info:"
    ]

    if country_name_or_id:
        lines.append(f"Country: <code>{country_name_or_id}</code>")
    if region_name_or_id:
        lines.append(f"Region: <code>{region_name_or_id}</code>")
    if city_name:
        lines.append(f"City: <code>{city_name}</code>")
    if brand_name_or_id:
        lines.append(f"Brand: <code>{brand_name_or_id}</code>")
    if car_model_name:
        lines.append(f"Car-model: <code>{car_model_name}</code>")

    lines.append("Status: <b>Need to add</b>")

    text = "\n".join(lines)

    await bot.send_message(chat_id=settings.telegram_group_id, text=text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("checking_task:"))
async def handle_get_task(callback: CallbackQuery):
    task_id = callback.data.split(':')[1]
    new_text = callback.message.html_text.replace(
        "Status: <b>Need to add</b>",
        "Status: <b>In progress</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Create", callback_data=f"complete:{task_id}"),
            InlineKeyboardButton(text="Ignore and ban", callback_data=f"ignore and ban:{task_id}"),
            InlineKeyboardButton(text="Manual creating or ignore", callback_data=f"ignore:{task_id}"),
        ]
    ])
    await callback.message.edit_text(new_text, reply_markup=keyboard)
    await callback.answer("Task taken. Status updated.")


@dp.callback_query(F.data.startswith("complete:"))
async def handle_auto_created(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    data = await collection.find_one({"_id": task_id}, projection={"_id": False, 'created_at': False})

    if not data:
        await callback.answer("Error: Task data not found.")
        return

    new_text = callback.message.html_text.replace(
        "Status: <b>In progress</b>",
        "Status: <b>Created</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)

    from app.tasks import manage_additional_info_from_bot
    manage_additional_info_from_bot.delay(task='create', **data)

    await collection.delete_one({"_id": task_id})
    await callback.answer("Marked as created.")


@dp.callback_query(F.data.startswith("ignore and ban:"))
async def handle_ignore_and_ban(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    data = await collection.find_one({"_id": task_id}, projection={"_id": False, 'created_at': False})

    if not data:
        await callback.answer("Error: Task data not found.")
        return

    new_text = callback.message.html_text.replace(
        "Status: <b>In progress</b>",
        "Status: <b>Banned</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)

    from app.tasks import manage_additional_info_from_bot
    manage_additional_info_from_bot.delay(task='ban_user', **data)

    await collection.delete_one({"_id": task_id})
    await callback.answer("Marked as banned.")


@dp.callback_query(F.data.startswith("ignore:"))
async def handle_manual_checker(callback: CallbackQuery):
    task_id = callback.data.split(':')[1]
    new_text = callback.message.html_text.replace(
        "Status: <b>In progress</b>",
        "Status: <b>Manual Checking</b>",
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Creating", callback_data=f"manual_creating:{task_id}"),
            InlineKeyboardButton(text="Ignore", callback_data=f"skip:{task_id}"),
        ]
    ])
    await callback.message.edit_text(new_text, reply_markup=keyboard)
    await callback.answer("Task taken for manual. Status updated.")


@dp.callback_query(F.data.startswith("manual_creating:"))
async def handle_ignore_and_ban(callback: CallbackQuery):

    new_text = callback.message.html_text.replace(
        "Status: <b>Manual Checking</b>",
        "Status: <b>Created</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)
    await callback.answer("Marked as manual_created.")


@dp.callback_query(F.data.startswith("skip:"))
async def handle_ignore_and_ban(callback: CallbackQuery):

    new_text = callback.message.html_text.replace(
        "Status: <b>Manual Checking</b>",
        "Status: <b>Ignored</b>"
    )
    await callback.message.edit_text(new_text, reply_markup=None)
    await callback.answer("Marked as ignored.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
