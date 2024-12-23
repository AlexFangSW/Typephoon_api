from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from ..types.jwt import JWTPayload
from ..types.setting import Setting
import jwt


@dataclass(slots=True)
class GenTokenPairRet:
    access_token: str
    refresh_token: str


class TokenGenerator:

    def __init__(self, setting: Setting) -> None:
        self._setting = setting

    def gen_access_token(self, user_id: str, username: str) -> str:
        iat = datetime.now(UTC)
        nbf = (iat - timedelta(seconds=1))
        exp = iat + timedelta(seconds=self._setting.token.access_duration)
        payload = JWTPayload(sub=user_id,
                             name=username,
                             exp=int(exp.timestamp()),
                             nbf=int(nbf.timestamp()),
                             iat=int(iat.timestamp()))

        return jwt.encode(asdict(payload),
                          self._setting.token.private_key,
                          algorithm="RS256")

    def gen_refresh_token(self, user_id: str, username: str) -> str:
        iat = datetime.now(UTC)
        nbf = (iat - timedelta(seconds=1))
        exp = iat + timedelta(seconds=self._setting.token.refresh_duration)
        payload = JWTPayload(sub=user_id,
                             name=username,
                             exp=int(exp.timestamp()),
                             nbf=int(nbf.timestamp()),
                             iat=int(iat.timestamp()))
        return jwt.encode(asdict(payload),
                          self._setting.token.private_key,
                          algorithm="RS256")

    def gen_token_pair(self, user_id: str, username: str) -> GenTokenPairRet:
        """
        access token + refresh token
        """
        access_token = self.gen_access_token(user_id, username)

        refresh_token = self.gen_refresh_token(user_id, username)

        return GenTokenPairRet(access_token=access_token,
                               refresh_token=refresh_token)
