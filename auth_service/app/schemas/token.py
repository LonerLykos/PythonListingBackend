from pydantic import BaseModel, Field, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)
