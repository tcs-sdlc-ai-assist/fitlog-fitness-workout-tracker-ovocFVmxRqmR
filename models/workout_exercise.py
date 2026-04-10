import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from database import Base


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    notes = Column(String(500), nullable=True)

    workout = relationship("Workout", back_populates="exercises", lazy="selectin")
    exercise = relationship("Exercise", back_populates="workout_exercises", lazy="selectin")
    sets = relationship("WorkoutSet", back_populates="workout_exercise", lazy="selectin", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<WorkoutExercise(id={self.id}, workout_id={self.workout_id}, exercise_id={self.exercise_id}, order_index={self.order_index})>"