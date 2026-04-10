import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class TemplateExercise(Base):
    __tablename__ = "template_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("workout_templates.id", ondelete="CASCADE"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    sets_count = Column(Integer, nullable=True, default=3)
    default_reps = Column(Integer, nullable=True, default=10)
    default_weight = Column(Float, nullable=True)

    template = relationship("WorkoutTemplate", back_populates="exercises", lazy="selectin")
    exercise = relationship("Exercise", back_populates="template_exercises", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<TemplateExercise(id={self.id}, template_id={self.template_id}, "
            f"exercise_id={self.exercise_id}, order_index={self.order_index})>"
        )