import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="templates", lazy="selectin")
    template_exercises = relationship(
        "TemplateExercise",
        back_populates="template",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="TemplateExercise.order_index",
    )