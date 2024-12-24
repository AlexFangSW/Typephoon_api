from pydantic import BaseModel, ConfigDict


class UserNameAndID(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
