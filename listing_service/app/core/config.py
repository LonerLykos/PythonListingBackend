from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    access_token_secret_key: str
    algorithm: str

    media_root: str
    media_url: str

    # REDIS
    redis_scheme: str
    redis_host: str
    redis_port: int
    redis_db_index: int

    #DB
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_host: str
    mysql_port: int

    @property
    def redis_url(self) -> str:
        return (
            f"{self.redis_scheme}://{self.redis_host}"
            f":{self.redis_port}/{self.redis_db_index}"
        )

    @property
    def listing_db_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    model_config = SettingsConfigDict(case_sensitive=False)

settings = Settings()
