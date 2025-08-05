import aio_pika
import json
from shared.utils.logging import setup_logging
from shared.config import rabbitmq_config

logger = setup_logging()


async def get_rabbitmq_connection():
    try:
        connection = await aio_pika.connect_robust(rabbitmq_config.rabbitmq_url)
        logger.info("Connected to RabbitMQ")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
        raise


async def publish_event(queue_name: str, event_type: str, data: dict):
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(queue_name, durable=True)
        message = aio_pika.Message(
            body=json.dumps({"type": event_type, "data": data}).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        await channel.default_exchange.publish(message, routing_key=queue_name)
        logger.info(f"Published event {event_type} to queue {queue_name}")
