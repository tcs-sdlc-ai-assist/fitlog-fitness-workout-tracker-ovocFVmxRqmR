from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExerciseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Exercise name")
    muscle_group: str = Field(..., min_length=1, max_length=100, description="Target muscle group")
    equipment: str = Field(..., min_length=1, max_length=100, description="Required equipment")
    instructions: Optional[str] = Field(None, max_length=2000, description="Exercise instructions")

    @field_validator("name", "muscle_group", "equipment")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace only")
        return stripped

    @field_validator("instructions")
    @classmethod
    def strip_instructions(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class ExerciseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Exercise name")
    muscle_group: Optional[str] = Field(None, min_length=1, max_length=100, description="Target muscle group")
    equipment: Optional[str] = Field(None, min_length=1, max_length=100, description="Required equipment")
    instructions: Optional[str] = Field(None, max_length=2000, description="Exercise instructions")

    @field_validator("name", "muscle_group", "equipment")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field must not be empty or whitespace only")
            return stripped
        return v

    @field_validator("instructions")
    @classmethod
    def strip_instructions(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    muscle_group: str
    equipment: str
    instructions: Optional[str] = None
    is_system: bool
    created_by: Optional[int] = None
    created_at: datetime


class ExerciseListResponse(BaseModel):
    exercises: list[ExerciseResponse]
    total: int
    page: int
    page_size: int
    total_pages: int