from enum import IntEnum, StrEnum


class ErrorCode(StrEnum):
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    REFRESH_TOKEN_MISSMATCH = "REFRESH_TOKEN_MISSMATCH"
    INVALID_TOKEN = "INVALID_TOKEN"


class OAuthProviders(StrEnum):
    GOOGLE = "google"


class CookieNames(StrEnum):
    ACCESS_TOKEN = "TP_AT"
    REFRESH_TOKEN = "TP_RT"
    USERNAME = "USERNAME"


class WSCloseReason(StrEnum):
    INVALID_TOKEN = "INVALID_TOKEN"


class UserType(StrEnum):
    GUEST = "GUEST"
    REGISTERED = "REGISTERED"


class GameStatus(IntEnum):
    LOBBY = 0
    IN_GAME = 1


class GameCacheType(StrEnum):
    PLAYERS = "players"
    COUNTDOWN = "countdown"
