from datetime import datetime
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class User(Base):
    """
    Attributes:
        id: User ID 
            - {PREFIX}_{ID}_{TS}
            - ex: google_1234567890_1717293420

        name: User name
            - Default to email username or auto generated username

        registered_at: User registered at
            - Default to current timestamp

        type: User type
            - ex: "guest", "registered"
        
        refresh_token
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
    type: Mapped[int] = mapped_column()
    refresh_token: Mapped[str | None] = mapped_column(Text())

    game_results = relationship(
        "GameResultModel",
        back_populates="user",
        passive_deletes=True,
        uselist=True,
    )
