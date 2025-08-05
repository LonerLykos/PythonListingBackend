from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.config import rabbitmq_config


class Settings(BaseSettings):

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    sender_email: str

    # MongoDB
    mongo_db_url: str
    mongo_initdb_database: str
    mongodb_ttl_seconds: int

    auth_db_url: str
    listing_db_url: str

    rabbitmq_url: str = rabbitmq_config.rabbitmq_url
    privat_exchange_url: str

    telegram_bot_token: str
    telegram_group_id: int

    model_config = SettingsConfigDict(case_sensitive=False)

settings = Settings()
