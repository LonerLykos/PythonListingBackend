from datetime import date
from typing import Annotated
from pydantic import BaseModel, EmailStr, StringConstraints, ConfigDict

UsernameStr = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=50,
        pattern=r'^[A-Z][a-z0-9]*$'
    )
]


class UserBase(BaseModel):
    auth_user_id: int
    username: UsernameStr
    email: EmailStr
    is_superadmin: bool


class User(UserBase):
    id: int
    is_banned: bool
    role_id: int
    is_premium: bool
    premium_expires_at: date | None

    model_config = ConfigDict(from_attributes=True)
