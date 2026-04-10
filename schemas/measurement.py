from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class MeasurementCreate(BaseModel):
    measurement_date: date
    weight: Optional[float] = None
    body_fat_percent: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    thighs: Optional[float] = None

    @field_validator(
        "weight",
        "body_fat_percent",
        "chest",
        "waist",
        "hips",
        "arms",
        "thighs",
        mode="before",
    )
    @classmethod
    def validate_positive(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError(f"{info.field_name} must be a positive number")
        return v

    @field_validator("body_fat_percent", mode="before")
    @classmethod
    def validate_body_fat_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 100:
            raise ValueError("body_fat_percent must be between 0 and 100")
        return v


class MeasurementUpdate(BaseModel):
    measurement_date: Optional[date] = None
    weight: Optional[float] = None
    body_fat_percent: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    thighs: Optional[float] = None

    @field_validator(
        "weight",
        "body_fat_percent",
        "chest",
        "waist",
        "hips",
        "arms",
        "thighs",
        mode="before",
    )
    @classmethod
    def validate_positive(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError(f"{info.field_name} must be a positive number")
        return v

    @field_validator("body_fat_percent", mode="before")
    @classmethod
    def validate_body_fat_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 100:
            raise ValueError("body_fat_percent must be between 0 and 100")
        return v


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    measurement_date: date
    weight: Optional[float] = None
    body_fat_percent: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    arms: Optional[float] = None
    thighs: Optional[float] = None
    created_at: datetime


class MeasurementListResponse(BaseModel):
    measurements: list[MeasurementResponse]
    total: int
    page: int
    page_size: int


class TrendDataPoint(BaseModel):
    date: date
    value: Optional[float] = None


class TrendSummary(BaseModel):
    metric: str
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    data_points: list[TrendDataPoint] = []