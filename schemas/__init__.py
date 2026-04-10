import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from schemas.exercise import (
    ExerciseCreate,
    ExerciseUpdate,
    ExerciseResponse,
    ExerciseListResponse,
)
from schemas.workout import (
    SetCreate,
    SetResponse,
    WorkoutExerciseCreate,
    WorkoutExerciseResponse,
    WorkoutExerciseDetailResponse,
    PRUpdate,
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutResponse,
    WorkoutCreateResponse,
    WorkoutDetailResponse,
    WorkoutListResponse,
)
from schemas.template import (
    TemplateExerciseCreate,
    TemplateExerciseResponse,
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
)
from schemas.measurement import (
    MeasurementCreate,
    MeasurementUpdate,
    MeasurementResponse,
    MeasurementListResponse,
    TrendDataPoint,
    TrendSummary,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "ExerciseCreate",
    "ExerciseUpdate",
    "ExerciseResponse",
    "ExerciseListResponse",
    "SetCreate",
    "SetResponse",
    "WorkoutExerciseCreate",
    "WorkoutExerciseResponse",
    "WorkoutExerciseDetailResponse",
    "PRUpdate",
    "WorkoutCreate",
    "WorkoutUpdate",
    "WorkoutResponse",
    "WorkoutCreateResponse",
    "WorkoutDetailResponse",
    "WorkoutListResponse",
    "TemplateExerciseCreate",
    "TemplateExerciseResponse",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "MeasurementCreate",
    "MeasurementUpdate",
    "MeasurementResponse",
    "MeasurementListResponse",
    "TrendDataPoint",
    "TrendSummary",
]