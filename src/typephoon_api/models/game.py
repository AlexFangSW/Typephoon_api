from datetime import datetime
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .game_result import GameResult

from .util import BigSerial
from .base import Base


class Game(Base):
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

    id: Mapped[int] = mapped_column(BigSerial(), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                               nullable=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                             nullable=True)
    status: Mapped[int] = mapped_column(nullable=False)
    invite_token: Mapped[str] = mapped_column(Text(), nullable=True)
    type: Mapped[int] = mapped_column(nullable=False)

    game_results = relationship("GameResult",
                                back_populates="game",
                                passive_deletes=True,
                                uselist=True)
