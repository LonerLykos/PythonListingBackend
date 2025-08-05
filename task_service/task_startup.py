import asyncio
import subprocess
from app.python_ria_bot import init_mongo
from shared.utils import setup_logging

logger = setup_logging()


async def init_services():
    logger.info("Initializing MongoDB TTL index...")
    await init_mongo()
    logger.info("MongoDB initialized successfully.")


def run():
    asyncio.run(init_services())

    logger.info("Running run_on_startup.py...")
    subprocess.run(["poetry", "run", "python", "app/run_on_startup.py"], check=True)

    logger.info("Starting email_consumer.py in background...")
    subprocess.Popen(["poetry", "run", "python", "app/email_consumer.py"])

    logger.info("Starting bot_mails_consumer.py in background...")
    subprocess.Popen(["poetry", "run", "python", "app/bot_mails_consumer.py"])

    logger.info("Starting Telegram bot in background...")
    subprocess.Popen(["poetry", "run", "python", "app/python_ria_bot.py"])

    logger.info("Starting Celery worker...")
    subprocess.run([
        "poetry", "run", "celery", "-A", "app.celery_app:app",
        "worker", "--beat", "--loglevel=info"
    ])


if __name__ == "__main__":
    run()
