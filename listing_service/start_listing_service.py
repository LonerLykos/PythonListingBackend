import asyncio
from shared.utils.logging import setup_logging

logger = setup_logging()


async def main():
    await asyncio.create_subprocess_exec("poetry", "run", "python", "app/user_rabbitmq_consumer.py")
    logger.info("Consumer started")

    server = await asyncio.create_subprocess_exec("uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000")
    logger.info("Listing service started")

    await server.wait()


if __name__ == "__main__":
    asyncio.run(main())
