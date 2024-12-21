from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    scope: str
    id_token: str
