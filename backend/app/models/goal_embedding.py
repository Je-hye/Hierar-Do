from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class GoalEmbedding(Base):
    __tablename__ = "goal_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content_summary: Mapped[str] = mapped_column(String)
    
    # OpenAI text-embedding-3-small uses 1536 dimensions
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
