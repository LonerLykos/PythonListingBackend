import asyncio
import json
from app.config import settings
from shared.utils.logging import setup_logging
from shared.utils.rabbitmq import get_rabbitmq_connection
from shared.utils import constants as rb_const
from utils.handle_bot_events import handle_event

logger = setup_logging()


async def consume_notify_events():
    """Listens to admin_notify_events from RabbitMQ and sends Telegram notifications using bot."""
    logger.debug(f"Using RABBITMQ_URL: {settings.rabbitmq_url}")
    while True:
        try:
            connection = await get_rabbitmq_connection()
            logger.info("Connected to RabbitMQ")
            channel = await connection.channel()
            queue = await channel.declare_queue(rb_const.RABBITMQ_QUEUE_ADMIN_EVENTS, durable=True)

            queue_iter = queue.iterator()
            async for message in queue_iter:
                try:
                    payload = json.loads(message.body.decode())
                    logger.debug(f"Raw message: {payload}")
                    if "data" not in payload or "type" not in payload:
                        logger.error(f"Missing 'data' or 'type' in payload, {payload}")
                        await message.ack()
                        continue

                    await handle_event(payload["type"], payload["data"])
                    await message.ack()

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    await message.nack(requeue=True)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    await message.nack(requeue=True)
        except Exception as e:
            logger.error(f"Error consuming email events: {str(e)}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logger.info("Starting RabbitMQ consumer for email events...")
    asyncio.run(consume_notify_events())