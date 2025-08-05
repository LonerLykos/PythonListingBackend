import asyncio
import json
from shared.utils.logging import setup_logging
from shared.utils.rabbitmq import get_rabbitmq_connection
from celery_app import app as celery_app
from shared.utils import constants as rb_const

logger = setup_logging()


async def consume_email_events():
    """Listens to email_events from RabbitMQ and starts a Celery task."""
    logger.debug(f"Using RABBITMQ_URL: {celery_app.conf.broker_url}")
    while True:
        try:
            connection = await get_rabbitmq_connection()
            logger.info("Connected to RabbitMQ")
            channel = await connection.channel()
            queue = await channel.declare_queue(rb_const.RABBITMQ_QUEUE_EMAIL_EVENTS, durable=True)

            queue_iter = queue.iterator()
            async for message in queue_iter:
                try:
                    payload = json.loads(message.body.decode())
                    logger.debug(f"Raw message: {payload}")
                    if "data" not in payload or "type" not in payload or payload["type"] != rb_const.EVENT_EMAIL_SEND:
                        logger.error(f"Invalid payload: {payload}")
                        await message.ack()
                        continue

                    data = payload["data"]
                    required_keys = ["email", "subject", "context", "template_name"]
                    missing_keys = [key for key in required_keys if key not in data]
                    if missing_keys:
                        logger.error(f"Missing keys in data: {missing_keys}")
                        await message.ack()
                        continue

                    logger.debug(f"Queueing email task for {data['email']}")
                    celery_app.send_task(
                        "app.tasks.send_email",
                        kwargs={
                            "email": data["email"],
                            "subject": data["subject"],
                            "context": data["context"],
                            "template_name": data["template_name"]
                        }
                    )
                    logger.info(f"Waiting email task for {data['email']}")
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
    asyncio.run(consume_email_events())
