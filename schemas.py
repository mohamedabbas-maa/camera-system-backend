from pydantic import BaseModel, ConfigDict


class CameraBase(BaseModel):
    name: str
    ip: str
    username: str
    password: str
    location: str | None = None
    enabled: bool = True


class CameraCreate(CameraBase):
    model_config = ConfigDict(from_attributes=True)


class CameraUpdate(BaseModel):
    name: str | None = None
    ip: str | None = None
    username: str | None = None
    password: str | None = None
    location: str | None = None
    enabled: bool | None = None


class CameraOut(CameraBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
