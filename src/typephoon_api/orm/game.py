from datetime import datetime
from sqlalchemy import DateTime, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .custom import BigSerial
from .base import Base
from enum import IntEnum


class GameType(IntEnum):
    SINGLE = 0
    RANDOM = 1
    TEAM = 2


class GameStatus(IntEnum):
    LOBBY = 0
    IN_GAME = 1
    FINISHED = 2


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(
        BigSerial(),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[int] = mapped_column()
    invite_token: Mapped[str | None] = mapped_column(Text())
    game_type: Mapped[int] = mapped_column()

    player_count: Mapped[int] = mapped_column(server_default=text("0"))
    finish_count: Mapped[int] = mapped_column(server_default=text("0"))

    game_results = relationship(
        "GameResult",
        back_populates="game",
        passive_deletes=True,
        uselist=True,
    )
