import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.exercise import Exercise
from models.workout import Workout, WorkoutExercise
from models.set import Set
from models.personal_record import PersonalRecord


async def search_exercises(
    db: AsyncSession,
    query: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Search exercises with optional filters and pagination."""
    stmt = select(Exercise)
    count_stmt = select(func.count(Exercise.id))

    conditions = []

    if query and query.strip():
        search_term = f"%{query.strip()}%"
        conditions.append(Exercise.name.ilike(search_term))

    if muscle_group and muscle_group.strip():
        conditions.append(Exercise.muscle_group == muscle_group.strip())

    if equipment and equipment.strip():
        conditions.append(Exercise.equipment == equipment.strip())

    if conditions:
        stmt = stmt.where(and_(*conditions))
        count_stmt = count_stmt.where(and_(*conditions))

    # Get total count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Calculate pagination
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * page_size

    # Get paginated results
    stmt = stmt.order_by(Exercise.name.asc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    exercises = result.scalars().all()

    return {
        "exercises": list(exercises),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_exercise_by_id(
    db: AsyncSession,
    exercise_id: int,
) -> Optional[Exercise]:
    """Get a single exercise by ID."""
    stmt = select(Exercise).where(Exercise.id == exercise_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_exercise_detail(
    db: AsyncSession,
    exercise_id: int,
) -> Optional[Exercise]:
    """Get exercise detail with related data."""
    stmt = (
        select(Exercise)
        .where(Exercise.id == exercise_id)
        .options(
            selectinload(Exercise.personal_records),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def add_exercise(
    db: AsyncSession,
    name: str,
    muscle_group: str,
    equipment: str,
    instructions: Optional[str] = None,
    is_system: bool = True,
    created_by: Optional[int] = None,
) -> Exercise:
    """Create a new exercise."""
    exercise = Exercise(
        name=name.strip(),
        muscle_group=muscle_group.strip(),
        equipment=equipment.strip(),
        instructions=instructions.strip() if instructions else None,
        is_system=is_system,
        created_by=created_by,
    )
    db.add(exercise)
    await db.flush()
    await db.refresh(exercise)
    return exercise


async def edit_exercise(
    db: AsyncSession,
    exercise_id: int,
    name: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    instructions: Optional[str] = None,
    is_system: Optional[bool] = None,
) -> Optional[Exercise]:
    """Update an existing exercise."""
    stmt = select(Exercise).where(Exercise.id == exercise_id)
    result = await db.execute(stmt)
    exercise = result.scalar_one_or_none()

    if exercise is None:
        return None

    if name is not None:
        exercise.name = name.strip()
    if muscle_group is not None:
        exercise.muscle_group = muscle_group.strip()
    if equipment is not None:
        exercise.equipment = equipment.strip()
    if instructions is not None:
        stripped = instructions.strip()
        exercise.instructions = stripped if stripped else None
    if is_system is not None:
        exercise.is_system = is_system

    await db.flush()
    await db.refresh(exercise)
    return exercise


async def delete_exercise(
    db: AsyncSession,
    exercise_id: int,
) -> bool:
    """Delete an exercise by ID. Returns True if deleted, False if not found."""
    stmt = select(Exercise).where(Exercise.id == exercise_id)
    result = await db.execute(stmt)
    exercise = result.scalar_one_or_none()

    if exercise is None:
        return False

    await db.delete(exercise)
    await db.flush()
    return True


async def get_exercise_history_for_user(
    db: AsyncSession,
    exercise_id: int,
    user_id: int,
    limit: int = 20,
) -> list[dict]:
    """Get recent workout history for a specific exercise and user.

    Returns a list of dicts with: workout_id, date, set_number, weight, reps.
    """
    stmt = (
        select(
            Workout.id.label("workout_id"),
            Workout.date.label("date"),
            Set.weight.label("weight"),
            Set.reps.label("reps"),
            Set.order_index.label("set_order"),
        )
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .join(Set, Set.workout_exercise_id == WorkoutExercise.id)
        .where(
            and_(
                Workout.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
            )
        )
        .order_by(Workout.date.desc(), WorkoutExercise.order_index.asc(), Set.order_index.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    history = []
    for idx, row in enumerate(rows):
        history.append({
            "workout_id": row.workout_id,
            "date": row.date,
            "set_number": row.set_order + 1,
            "weight": row.weight,
            "reps": row.reps,
        })

    return history


async def get_exercise_prs(
    db: AsyncSession,
    exercise_id: int,
    user_id: int,
) -> list:
    """Get personal records for a specific exercise and user."""
    stmt = (
        select(PersonalRecord)
        .where(
            and_(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_id == exercise_id,
            )
        )
        .order_by(PersonalRecord.type.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_all_muscle_groups(db: AsyncSession) -> list[str]:
    """Get all distinct muscle groups from exercises."""
    stmt = (
        select(Exercise.muscle_group)
        .distinct()
        .order_by(Exercise.muscle_group.asc())
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all() if row[0]]


async def get_all_equipment_types(db: AsyncSession) -> list[str]:
    """Get all distinct equipment types from exercises."""
    stmt = (
        select(Exercise.equipment)
        .distinct()
        .order_by(Exercise.equipment.asc())
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all() if row[0]]


async def get_all_exercises(db: AsyncSession) -> list[Exercise]:
    """Get all exercises ordered by name (for dropdowns/selects)."""
    stmt = select(Exercise).order_by(Exercise.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_exercise_count(db: AsyncSession) -> int:
    """Get total number of exercises."""
    stmt = select(func.count(Exercise.id))
    result = await db.execute(stmt)
    return result.scalar() or 0


async def check_exercise_name_exists(
    db: AsyncSession,
    name: str,
    exclude_id: Optional[int] = None,
) -> bool:
    """Check if an exercise with the given name already exists."""
    stmt = select(func.count(Exercise.id)).where(
        func.lower(Exercise.name) == func.lower(name.strip())
    )
    if exclude_id is not None:
        stmt = stmt.where(Exercise.id != exclude_id)

    result = await db.execute(stmt)
    count = result.scalar() or 0
    return count > 0