from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TemplateExerciseCreate(BaseModel):
    exercise_id: int
    order_index: int

    @field_validator("exercise_id")
    @classmethod
    def exercise_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("exercise_id must be a positive integer")
        return v

    @field_validator("order_index")
    @classmethod
    def order_index_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("order_index must be non-negative")
        return v


class TemplateExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    exercise_id: int
    order_index: int
    exercise_name: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    is_system: bool = False
    exercises: list[TemplateExerciseCreate] = []

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Template name must not be empty")
        if len(v) > 200:
            raise ValueError("Template name must be 200 characters or fewer")
        return v


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    is_system: Optional[bool] = None
    exercises: Optional[list[TemplateExerciseCreate]] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Template name must not be empty")
            if len(v) > 200:
                raise ValueError("Template name must be 200 characters or fewer")
        return v


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    user_id: Optional[int] = None
    is_system: bool
    created_at: datetime
    exercises: list[TemplateExerciseResponse] = []