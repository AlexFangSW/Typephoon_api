from enum import IntEnum, StrEnum


class ErrorCode(StrEnum):
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"


class UserType(IntEnum):
    GUEST = 0
    REGISTERED = 1
