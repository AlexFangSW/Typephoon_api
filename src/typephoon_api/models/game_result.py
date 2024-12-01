from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, DateTime, PrimaryKeyConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class GameResult(Base):
    """
    Game result model

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

    game_id: Mapped[int] = mapped_column(BigInteger(), ForeignKey("games.id"))
    user_id: Mapped[str] = mapped_column(Text(), ForeignKey("users.id"))
    rank: Mapped[int] = mapped_column()
    wpm_raw: Mapped[float] = mapped_column()
    wpm_correct: Mapped[float] = mapped_column()
    accuracy: Mapped[float] = mapped_column()
    status: Mapped[int] = mapped_column()
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    role: Mapped[int] = mapped_column()
