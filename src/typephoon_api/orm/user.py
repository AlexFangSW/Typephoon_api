from datetime import datetime
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class User(Base):
    """
    Attributes:
        id: User ID 
            - {PREFIX}-{ID}
            - ex: google-1234567890
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        Text(),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(Text())
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    refresh_token: Mapped[str | None] = mapped_column(Text())

    game_results = relationship(
        "GameResult",
        back_populates="user",
        passive_deletes=True,
        uselist=True,
    )
