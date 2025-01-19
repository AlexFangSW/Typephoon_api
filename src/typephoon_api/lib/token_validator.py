from ..types.jwt import JWTPayload
from ..types.setting import Setting
import jwt


class TokenValidator:

    def __init__(self, setting: Setting) -> None:
        self._setting = setting

    def validate(self, token: str) -> JWTPayload:
        decoded_jwt = jwt.decode(
            jwt=token,
            key=self._setting.token.public_key,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
            },
            algorithms=["RS256"],
        )

        return JWTPayload.model_validate(decoded_jwt)
