import asyncio
import json
from shared.utils.logging import setup_logging
from shared.utils.rabbitmq import get_rabbitmq_connection
from shared.utils import constants as rb_const
from app.db.database import get_listing_session
from app.models.user import User
from sqlalchemy import insert, select

logger = setup_logging()


async def consume_user_events():
    """Listens to user_events from RabbiMQ and processes them."""
    logger.info("Starting to consume user events...")
    while True:
        try:
            connection = await get_rabbitmq_connection()
            channel = await connection.channel()
            queue = await channel.declare_queue(rb_const.RABBITMQ_QUEUE_USER_EVENTS, durable=True)

            queue_iter = queue.iterator()
            try:
                async for message in queue_iter:
                    try:
                        payload = json.loads(message.body.decode())
                        logger.debug(f"Received message: {payload}")
                        if payload.get("type") != rb_const.EVENT_USER_CREATED:
                            logger.warning("Unexpected event type, skipping")
                            await message.ack()
                            continue

                        data = payload.get("data")
                        logger.info(f"Creating user from event: {data}")

                        async with get_listing_session() as session:
                            result = await session.scalar(select(User).where(User.auth_user_id == data["id"]))
                            if result:
                                logger.error(f"User already exists in listing's service DB: {data['id']}")
                                raise Exception(f"You need to register a new user")

                            role = 3
                            if data["is_superadmin"]:
                                role = 1

                            await session.execute(
                                insert(User).values(
                                    auth_user_id=data["id"],
                                    email=data["email"],
                                    username=data["username"],
                                    is_superadmin=data["is_superadmin"],
                                    is_banned=False,
                                    is_premium=False,
                                    premium_expires_at=None,
                                    role_id=role
                                )
                            )
                            await session.commit()

                            logger.info(f"User created in user service DB: {data['id']}")
                            await message.ack()
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        await message.nack(requeue=True)
            finally:
                await queue_iter.close()
        except Exception as e:
            logger.error(f"Error consuming email events: {str(e)}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logger.info("Starting RabbitMQ consumer for email events...")
    asyncio.run(consume_user_events())