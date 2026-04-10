import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)

    user = relationship("User", back_populates="workouts", lazy="selectin")
    workout_exercises = relationship(
        "WorkoutExercise",
        back_populates="workout",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )
    personal_records = relationship(
        "PersonalRecord",
        back_populates="workout",
        lazy="selectin",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0)

    workout = relationship("Workout", back_populates="workout_exercises", lazy="selectin")
    exercise = relationship("Exercise", back_populates="workout_exercises", lazy="selectin")
    sets = relationship(
        "Set",
        back_populates="workout_exercise",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Set.order_index",
    )