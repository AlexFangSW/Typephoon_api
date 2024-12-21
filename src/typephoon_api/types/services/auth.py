from pydantic import BaseModel


class LoginRedirectData(BaseModel):
    url: str
    access_token: str
    refresh_token: str
    username: str
    refresh_endpoint: str
