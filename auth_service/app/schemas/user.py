from pydantic import BaseModel, EmailStr, model_validator, Field, ConfigDict
from pydantic.types import StringConstraints
from typing import Annotated

PasswordStr = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=16,
        pattern=r'^[\w\d!@#$%^&*()\-\+={}\[\]|\\:;"\'<>,.?/]+$'

    )
]

UsernameStr = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=50,
        pattern=r'^[A-Z][a-z0-9]*$'
    )
]


class User(BaseModel):
    email: EmailStr
    username: UsernameStr


class UserCreate(User):
    password: PasswordStr

    @model_validator(mode='after')
    def validate_password(self):
        value = self.password
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char in '!@#$%^&*()-+={}[]|\\:;"\'<>,.?/' for char in value):
            raise ValueError('Password must contain at least one special character')
        if ' ' in value:
            raise ValueError('Password must not contain spaces')
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: PasswordStr

    model_config = ConfigDict(from_attributes=True)


class UserResponse(User):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class RestoreRequest(BaseModel):
    email: EmailStr


class NewPasswordRequest(BaseModel):
    new_password: str
