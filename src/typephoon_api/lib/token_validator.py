from ..types.jwt import JWTPayload
from ..types.setting import Setting
import jwt


class TokenValidator:

    def __init__(self, setting: Setting) -> None:
        self._setting = setting

    def validate(self, token: str) -> JWTPayload:
        decoded_jwt = jwt.decode(jwt=token,
                                 key=self._setting.token.public_key,
                                 options={
                                     "verify_signature": True,
                                     "verify_aud": False,
                                     "verify_iss": False,
                                 },
                                 algorithms=["RS256"])

        return JWTPayload(sub=decoded_jwt['sub'],
                          name=decoded_jwt["name"],
                          exp=decoded_jwt["exp"],
                          nbf=decoded_jwt["nbf"],
                          iat=decoded_jwt["iat"],
                          user_type=decoded_jwt["user_type"])
