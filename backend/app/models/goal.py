import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Integer, String, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class GoalStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    done = "done"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, native_enum=False), nullable=False, default=GoalStatus.active
    )
    available_hours_weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    available_hours_weekend: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="goals")
    milestones = relationship(
        "Milestone", back_populates="goal", cascade="all, delete-orphan"
    )
