from app.tasks import fetch_exchange_rates
from shared.utils.logging import setup_logging

logger = setup_logging()

if __name__ == "__main__":
    logger.info("Running fetch_exchange_rates on container startup")
    fetch_exchange_rates.delay()
