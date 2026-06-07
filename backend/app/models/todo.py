from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    milestone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("milestones.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suggested_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    milestone = relationship("Milestone", back_populates="todos")
