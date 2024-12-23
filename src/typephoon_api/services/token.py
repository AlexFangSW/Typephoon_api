from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from .base import ServiceRet

from ..types.jwt import JWTPayload
from ..types.setting import Setting
import jwt


@dataclass(slots=True)
class GenerateTokensRet:
    access_token: str
    refresh_token: str


class TokenService:

    def __init__(self, setting: Setting) -> None:
        self._setting = setting

    def gen_access_token(self, user_id: str, username: str) -> ServiceRet[str]:
        iat = datetime.now(UTC)
        nbf = (iat - timedelta(seconds=1))
        exp = iat + timedelta(seconds=self._setting.token.access_duration)
        payload = JWTPayload(sub=user_id,
                             name=username,
                             exp=int(exp.timestamp()),
                             nbf=int(nbf.timestamp()),
                             iat=int(iat.timestamp()))

        token = jwt.encode(asdict(payload),
                           self._setting.token.private_key,
                           algorithm="RS256")
        return ServiceRet(ok=True, data=token)

    def gen_refresh_token(self, user_id: str, username: str) -> ServiceRet[str]:
        iat = datetime.now(UTC)
        nbf = (iat - timedelta(seconds=1))
        exp = iat + timedelta(seconds=self._setting.token.refresh_duration)
        payload = JWTPayload(sub=user_id,
                             name=username,
                             exp=int(exp.timestamp()),
                             nbf=int(nbf.timestamp()),
                             iat=int(iat.timestamp()))
        token = jwt.encode(asdict(payload),
                           self._setting.token.private_key,
                           algorithm="RS256")

        return ServiceRet(ok=True, data=token)

    def gen_token_pair(self, user_id: str,
                       username: str) -> ServiceRet[GenerateTokensRet]:
        """
        access token + refresh token
        """
        access_token_ret = self.gen_access_token(user_id, username)
        assert access_token_ret.ok
        assert access_token_ret.data

        refresh_token_ret = self.gen_refresh_token(user_id, username)
        assert refresh_token_ret.ok
        assert refresh_token_ret.data

        return ServiceRet(ok=True,
                          data=GenerateTokensRet(
                              access_token=access_token_ret.data,
                              refresh_token=refresh_token_ret.data))
