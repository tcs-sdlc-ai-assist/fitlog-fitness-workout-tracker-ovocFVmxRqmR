import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import (
    Column,
    Integer,
    Float,
    Text,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    __table_args__ = (
        UniqueConstraint("user_id", "measurement_date", name="uq_user_measurement_date"),
        Index("idx_measurements_user_date", "user_id", "measurement_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_date = Column(Date, nullable=False)
    weight = Column(Float, nullable=True)
    body_fat_percent = Column(Float, nullable=True)
    chest = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hips = Column(Float, nullable=True)
    arms = Column(Float, nullable=True)
    thighs = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="measurements", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<BodyMeasurement(id={self.id}, user_id={self.user_id}, "
            f"date={self.measurement_date}, weight={self.weight})>"
        )