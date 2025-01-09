from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, DateTime, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class GameResult(Base):
    """
    Game result (per user)
    """

    __tablename__ = "game_results"
    __table_args__ = (PrimaryKeyConstraint("game_id", "user_id"),)

    game_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("games.id", ondelete="CASCADE"),
    )
    user_id: Mapped[str] = mapped_column(
        Text(),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    rank: Mapped[int] = mapped_column()
    wpm_raw: Mapped[float] = mapped_column()
    wpm_correct: Mapped[float] = mapped_column()
    accuracy: Mapped[float] = mapped_column()
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    game = relationship(
        "Game",
        foreign_keys=game_id,
        back_populates="game_results",
    )
    user = relationship(
        "User",
        foreign_keys=user_id,
        back_populates="game_results",
    )
