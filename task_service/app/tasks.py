import asyncio
import os
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, delete, update
from celery import shared_task
from shared.utils.logging import setup_logging
from aiosmtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from app.config import settings
from app.celery_app import app as celery_app
from auth_service.app.models.auth import ActiveToken, BlacklistedToken
from auth_service.app.models.auth import User as UserAuthModel
from listing_service.app import models
from listing_service.app.models.listing import Listing as ListingModel
from listing_service.app.models.user import User as UserListingModel
from listing_service.app.models.exchange_rate import ExchangeRate
from datetime import datetime, timezone, date
from app.utils.additional_check_or_create import (
    get_or_create_country,
    get_or_create_region,
    create_city,
    get_or_create_brand,
    create_carmodel
)

logger = setup_logging()

template_dir = os.path.join(os.path.dirname(__file__), "../templates")
env = Environment(loader=FileSystemLoader(template_dir))


# EMAIL_TASKS
async def send_email_async(email: str, subject: str, context: dict, template_name: str) :
    """Send email using a Jinja2 template."""

    subject_text = {
        'Verify Your Account': f'Please {context.get("username")} verify your account by visiting: {context.get("verify_url")}\n',
        'Request for changing password': f'Hello {context.get("username")}, you can restore your password by visiting: {context.get("restore_url")}\n',
    }

    try:
        template = env.get_template(template_name)
        html_content = template.render(**context)

        plain_text = subject_text.get(subject)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.sender_email
        msg["To"] = email

        part1 = MIMEText(plain_text, "plain")
        part2 = MIMEText(html_content, "html")
        msg.attach(part1)
        msg.attach(part2)

        smtp = SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
        )
        await smtp.connect()
        logger.debug("SMTP connection established")
        await smtp.login(settings.smtp_username, settings.smtp_password)
        logger.debug("SMTP login successful")

        await smtp.send_message(msg, recipients=[email])

        await smtp.quit()
        logger.info(f"Email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        raise


@celery_app.task(name="app.tasks.send_email")
def send_email(email: str, subject: str, context: dict, template_name: str):
    """Celery-tasks for sending email."""
    try:
        asyncio.run(send_email_async(email, subject, context, template_name))
    except Exception as e:
        logger.error(f"Celery task failed to send email to {email}: {str(e)}")
        raise


# TOKEN_TASKS
@shared_task
def clean_expired_tokens():
    """Checking active_tokens and remove old to blacklisted_tokens."""
    async def run_cleanup():
        engine = create_async_engine(settings.auth_db_url, echo=False)
        async with AsyncSession(engine) as session:
            try:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                result = await session.execute(
                    select(ActiveToken).where(ActiveToken.expires_at < now)
                )
                expired_tokens: list[ActiveToken] = list(result.scalars().all())

                if not expired_tokens:
                    logger.info("No expired tokens found")
                    return

                for token in expired_tokens:
                    if token.token_type == "email_verify":
                        user = await session.get(UserAuthModel, token.user_id)
                        await session.delete(user)

                    blacklisted = BlacklistedToken(
                        token=token.token,
                    )
                    session.add(blacklisted)
                    await session.execute(
                        delete(ActiveToken).where(ActiveToken.id == token.id)
                    )
                    logger.info(f"Blacklisted expired token: {token.token}")

                await session.commit()
                logger.info(f"Blacklisted {len(expired_tokens)} tokens")
            except Exception as e:
                logger.error(f"Error cleaning tokens: {str(e)}")
                await session.rollback()
            finally:
                await engine.dispose()

    asyncio.run(run_cleanup())


# EXCHANGE_TASKS
async def fetch_exchange_rates_async():
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.privat_exchange_url)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched exchange rates: {data}")
            return data
    except httpx.HTTPError as e:
        logger.error(f"Error fetching exchange rates: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching exchange rates: {str(e)}")


async def process_exchange_rates(data):
    usd_rate = {}
    eur_rate = {}

    for rate in data:
        if rate["ccy"] == "USD":
            usd_rate = {'buy': rate["sale"], 'sell': rate["buy"]}
        elif rate["ccy"] == "EUR":
            eur_rate = {'buy': rate["sale"], 'sell': rate["buy"]}
        else:
            logger.error(f"Unknown exchange rate: {rate['ccy']}")

    if usd_rate and eur_rate:
        exchange_data = ExchangeRate(
            buy_usd=usd_rate["buy"],
            sell_usd=usd_rate["sell"],
            buy_eur=eur_rate["buy"],
            sell_eur=eur_rate["sell"],
        )
        engine = create_async_engine(settings.listing_db_url, echo=False)
        async with AsyncSession(engine) as session:
            try:
                session.add(exchange_data)
                await session.commit()
            except Exception as e:
                logger.error(f"Error adding exchange data: {str(e)}")
            finally:
                await engine.dispose()
    else:
        logger.error("Missing USD or EUR rate in exchange data")


@shared_task
def fetch_exchange_rates():
    try:
        data = asyncio.run(fetch_exchange_rates_async())
        if data:
            asyncio.run(process_exchange_rates(data))
            logger.info("Successfully fetched and processed exchange rates.")
    except Exception as e:
        logger.error(f"Celery task failed: {str(e)}")


# PREMIUM_CHECKER
@shared_task
def clean_expired_premium_status():
    """Checking premium status and remove it if expired."""
    async def run_checker():
        engine = create_async_engine(settings.listing_db_url, echo=False)
        async with AsyncSession(engine) as session:
            try:
                now = date.today()
                await session.execute(
                    update(UserListingModel)
                    .where(UserListingModel.premium_expires_at < now)
                    .values(
                        is_premium=False,
                        premium_expires_at=None
                    )
                )
                await session.commit()

                logger.info(f'All expired premium statuses are cleared')
            except Exception as e:
                logger.error(f"Error cleaning premium status: {str(e)}")
                await session.rollback()
            finally:
                await engine.dispose()

    asyncio.run(run_checker())


# Bot Manage Listings
@shared_task
def manage_listing_from_bot(listing_id: int, task: str):
    async def run_banner():
        engine = create_async_engine(settings.listing_db_url, echo=False)
        async with AsyncSession(engine) as session:
            try:
                listing: ListingModel | None = await session.get(ListingModel, listing_id)
                if not listing:
                    logger.error(f"Listing {listing_id} not found")
                user_id = listing.user_id
                if task == "ban":
                    await session.delete(listing)
                    user = await session.get(UserListingModel, user_id)
                    if not user:
                        logger.error(f"User {user_id} not found")
                    user.is_banned = True
                if task == "allow_publication":
                    listing.is_active = True

                await session.commit()
            except Exception as e:
                logger.error(f"Error with managing listings: {str(e)}")
            finally:
                await engine.dispose()

    asyncio.run(run_banner())


# Bot Manage Additional info
@shared_task
def manage_additional_info_from_bot(
        task: str,
        title: str,
        country_name_or_id: str | int |None,
        region_name_or_id: str | int | None,
        city_name: str | None,
        brand_name_or_id: str | int | None,
        car_model_name: str | None,
        who_ask_for: str):
    async def run_creator():
        engine = create_async_engine(settings.listing_db_url, echo=False)
        async with AsyncSession(engine) as session:
            try:
                if task == 'ban_user':
                    user = await session.get(UserListingModel, who_ask_for)
                    if not user:
                        logger.error(f"User {who_ask_for} not found")
                        return
                    user.is_banned = True
                elif task == 'create':
                    if title == 'add_country':
                        await get_or_create_country(session, country_name_or_id)
                    elif title == 'add_region':
                        country = await get_or_create_country(session, country_name_or_id)
                        await get_or_create_region(session, region_name_or_id, country.id)
                    elif title == 'add_city':
                        country = await get_or_create_country(session, country_name_or_id)
                        region = await get_or_create_region(session, region_name_or_id, country.id)
                        await create_city(session, city_name, region.id)
                    elif title == 'add_brand':
                        await get_or_create_brand(session, brand_name_or_id)
                    elif title == 'add_carmodel':
                        brand = await get_or_create_brand(session, brand_name_or_id)
                        await create_carmodel(session, car_model_name, brand.id)

                await session.commit()

            except Exception as e:
                logger.error(f"Error with managing listings: {str(e)}")
            finally:
                await engine.dispose()

    asyncio.run(run_creator())
