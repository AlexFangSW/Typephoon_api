from enum import StrEnum


class ErrorCode(StrEnum):
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    REFRESH_TOKEN_MISSMATCH = "REFRESH_TOKEN_MISSMATCH"
    INVALID_TOKEN = "INVALID_TOKEN"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"


class CookieNames(StrEnum):
    ACCESS_TOKEN = "TP_AT"
    REFRESH_TOKEN = "TP_RT"
    USERNAME = "USERNAME"


class WSCloseReason(StrEnum):
    INVALID_TOKEN = "INVALID_TOKEN"


class UserType(StrEnum):
    GUEST = "GUEST"
    REGISTERED = "REGISTERED"


# NOTE: replace QueueInType with WSConnectionType ?
class QueueInType(StrEnum):
    RECONNECT = "reconnect"
    NEW = "new"


class WSConnectionType(StrEnum):
    RECONNECT = "reconnect"
    NEW = "new"
