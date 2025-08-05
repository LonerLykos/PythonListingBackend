from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # JWT
    access_token_secret_key: str
    refresh_token_secret_key: str
    email_verify_secret_key: str
    algorithm: str
    access_token_expire_hours: int = 24
    refresh_token_expire_days: int = 7
    email_verify_expire_hours: int = 1

    # DB
    mysql_user: str
    mysql_password: str
    mysql_database: str
    mysql_host: str
    mysql_port: int

    frontend_url: str

    model_config = SettingsConfigDict(case_sensitive=False)

    @property
    def auth_db_url(self) -> str:
        return (
            f'mysql+asyncmy://{self.mysql_user}:{self.mysql_password}'
            f'@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}'
        )

settings = Settings()
