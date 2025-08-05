from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    auth_service_url: str
    listing_service_url: str

    model_config = SettingsConfigDict(case_sensitive=False)

settings = Settings()
