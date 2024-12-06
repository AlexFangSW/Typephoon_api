from datetime import datetime
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .util import BigSerial
from .base import Base


class GameModel(Base):
    """
    Game model

    Attributes:
        id: Game ID
        created_at: Game created at
        start_at: Game started at
        end_at: Game ended at
        status: Game status
        invite_token: Game invite token
        type: Game type
    """
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
    type: Mapped[int] = mapped_column()

    game_results = relationship(
        "GameResultModel",
        back_populates="game",
        passive_deletes=True,
        uselist=True,
    )
