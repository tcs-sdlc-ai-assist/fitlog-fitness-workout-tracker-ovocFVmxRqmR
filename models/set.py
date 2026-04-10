import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Set(Base):
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_exercise_id = Column(
        Integer,
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    weight = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    is_pr = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    workout_exercise = relationship(
        "WorkoutExercise",
        back_populates="sets",
        lazy="selectin",
    )