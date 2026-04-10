from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime


class SetCreate(BaseModel):
    weight: float
    reps: int
    order_index: int = 0

    @field_validator("weight")
    @classmethod
    def weight_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Weight must be positive")
        return v

    @field_validator("reps")
    @classmethod
    def reps_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Reps must be positive")
        return v


class SetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_exercise_id: int
    weight: float
    reps: int
    order_index: int


class WorkoutExerciseCreate(BaseModel):
    exercise_id: int
    order_index: int = 0
    sets: list[SetCreate]

    @field_validator("sets")
    @classmethod
    def sets_must_not_be_empty(cls, v: list[SetCreate]) -> list[SetCreate]:
        if len(v) == 0:
            raise ValueError("At least one set is required per exercise")
        return v


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_id: int
    exercise_id: int
    order_index: int


class WorkoutExerciseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_id: int
    exercise_id: int
    order_index: int
    sets: list[SetResponse] = []
    exercise_name: Optional[str] = None
    muscle_group: Optional[str] = None


class PRUpdate(BaseModel):
    exercise_id: int
    type: str
    new_value: float


class WorkoutCreate(BaseModel):
    date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    exercises: list[WorkoutExerciseCreate]
    save_as_template: bool = False
    template_name: Optional[str] = None

    @field_validator("exercises")
    @classmethod
    def exercises_must_not_be_empty(cls, v: list[WorkoutExerciseCreate]) -> list[WorkoutExerciseCreate]:
        if len(v) == 0:
            raise ValueError("At least one exercise is required")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v


class WorkoutUpdate(BaseModel):
    date: Optional[date] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    exercises: Optional[list[WorkoutExerciseCreate]] = None

    @field_validator("exercises")
    @classmethod
    def exercises_must_not_be_empty_if_provided(cls, v: Optional[list[WorkoutExerciseCreate]]) -> Optional[list[WorkoutExerciseCreate]]:
        if v is not None and len(v) == 0:
            raise ValueError("At least one exercise is required")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v


class WorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class WorkoutCreateResponse(BaseModel):
    workout_id: int
    pr_updates: list[PRUpdate] = []


class WorkoutDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    exercises: list[WorkoutExerciseDetailResponse] = []


class WorkoutListResponse(BaseModel):
    workouts: list[WorkoutResponse]
    total: int
    page: int
    page_size: int