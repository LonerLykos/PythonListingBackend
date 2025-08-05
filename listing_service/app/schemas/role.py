from pydantic import BaseModel, ConfigDict


class RoleId(BaseModel):
    role_id: int


class RoleBase(BaseModel):
    name: str


class Role(RoleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
