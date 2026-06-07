from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    available_hours: Mapped[dict] = mapped_column(
        JSON, nullable=False, default={"weekday": 2, "weekend": 4}
    )

    goals = relationship("Goal", back_populates="user")
