from pydantic import BaseModel, ConfigDict


class PermissionBase(BaseModel):
    name: str
    description: str | None = None


class PermissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class Permission(PermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
