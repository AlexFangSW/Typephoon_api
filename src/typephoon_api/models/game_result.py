from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, DateTime, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class GameResult(Base):
    """
    Game result model (per user)

    Attributes:
        game_id: Game ID
        user_id: User ID
        rank: Rank
        wpm_raw: Raw WPM
        wpm_correct: Correct WPM
        accuracy: Accuracy
        status: Game status for user
        finished_at: Game finished at
        role: Game role for user
    """
    __tablename__ = "game_results"
    __table_args__ = (PrimaryKeyConstraint("game_id", "user_id"),)

    game_id: Mapped[int] = mapped_column(
        BigInteger(), ForeignKey("games.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(
        Text(), ForeignKey("users.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(nullable=False)
    wpm_raw: Mapped[float] = mapped_column(nullable=False)
    wpm_correct: Mapped[float] = mapped_column(nullable=False)
    accuracy: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[int] = mapped_column(nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  nullable=False)
    role: Mapped[int] = mapped_column(nullable=False)

    game = relationship("Game",
                        foreign_keys=game_id,
                        back_populates="game_results")
    user = relationship("User",
                        foreign_keys=user_id,
                        back_populates="game_results")
