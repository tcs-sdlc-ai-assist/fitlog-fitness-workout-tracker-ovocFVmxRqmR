import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship

from database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    muscle_group = Column(String(100), nullable=False, index=True)
    equipment = Column(String(100), nullable=False)
    instructions = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workout_exercises = relationship(
        "WorkoutExercise",
        back_populates="exercise",
        lazy="selectin",
    )
    template_exercises = relationship(
        "TemplateExercise",
        back_populates="exercise",
        lazy="selectin",
    )
    personal_records = relationship(
        "PersonalRecord",
        back_populates="exercise",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, name='{self.name}', muscle_group='{self.muscle_group}')>"