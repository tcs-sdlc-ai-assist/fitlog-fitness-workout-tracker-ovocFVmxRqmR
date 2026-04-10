import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from database import Base


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=True)
    achieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", "type", name="uq_user_exercise_type"),
        Index("idx_pr_user_exercise_type", "user_id", "exercise_id", "type"),
        Index("idx_pr_user_id", "user_id"),
    )

    user = relationship("User", back_populates="personal_records", lazy="selectin")
    exercise = relationship("Exercise", back_populates="personal_records", lazy="selectin")
    workout = relationship("Workout", back_populates="personal_records", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<PersonalRecord(id={self.id}, user_id={self.user_id}, "
            f"exercise_id={self.exercise_id}, type='{self.type}', "
            f"value={self.value})>"
        )