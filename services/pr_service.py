import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.personal_record import PersonalRecord
from models.exercise import Exercise
from models.workout import Workout, WorkoutExercise
from models.set import Set


async def detect_prs(
    db: AsyncSession,
    user_id: int,
    workout_id: int,
) -> list[dict]:
    """
    Detect and upsert personal records for all exercises in a workout.
    Idempotent: safe to call multiple times for the same workout.
    Returns a list of dicts with exercise_id, type, and new_value for any new/updated PRs.
    """
    pr_updates: list[dict] = []

    # Get the workout with its exercises and sets
    workout_result = await db.execute(
        select(Workout)
        .where(and_(Workout.id == workout_id, Workout.user_id == user_id))
        .options(
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.sets)
        )
    )
    workout = workout_result.scalar_one_or_none()
    if workout is None:
        return pr_updates

    workout_date = workout.date

    for workout_exercise in workout.workout_exercises:
        exercise_id = workout_exercise.exercise_id
        sets = workout_exercise.sets

        if not sets:
            continue

        # Compute best values from this workout's sets for this exercise
        best_weight = max((s.weight for s in sets), default=0.0)
        best_reps = max((s.reps for s in sets), default=0)
        best_volume = max((s.weight * s.reps for s in sets), default=0.0)

        pr_candidates = [
            ("weight", float(best_weight)),
            ("reps", float(best_reps)),
            ("volume", float(best_volume)),
        ]

        for pr_type, new_value in pr_candidates:
            if new_value <= 0:
                continue

            # Get existing PR for this user/exercise/type
            existing_result = await db.execute(
                select(PersonalRecord).where(
                    and_(
                        PersonalRecord.user_id == user_id,
                        PersonalRecord.exercise_id == exercise_id,
                        PersonalRecord.type == pr_type,
                    )
                )
            )
            existing_pr = existing_result.scalar_one_or_none()

            if existing_pr is None:
                # No existing PR - create new one
                new_pr = PersonalRecord(
                    user_id=user_id,
                    exercise_id=exercise_id,
                    type=pr_type,
                    value=new_value,
                    workout_id=workout_id,
                    achieved_at=datetime.now(timezone.utc),
                )
                db.add(new_pr)
                pr_updates.append({
                    "exercise_id": exercise_id,
                    "type": pr_type,
                    "new_value": new_value,
                })
            elif new_value > existing_pr.value:
                # New value beats existing PR - update
                existing_pr.value = new_value
                existing_pr.workout_id = workout_id
                existing_pr.achieved_at = datetime.now(timezone.utc)
                pr_updates.append({
                    "exercise_id": exercise_id,
                    "type": pr_type,
                    "new_value": new_value,
                })

    await db.flush()
    return pr_updates


async def get_personal_records(
    db: AsyncSession,
    user_id: int,
) -> list[dict]:
    """
    Get all personal records for a user, grouped by exercise.
    Returns a list of dicts with exercise info and best values per type.
    """
    result = await db.execute(
        select(PersonalRecord)
        .where(PersonalRecord.user_id == user_id)
        .options(selectinload(PersonalRecord.exercise))
        .order_by(PersonalRecord.exercise_id, PersonalRecord.type)
    )
    prs = result.scalars().all()

    # Group by exercise
    exercise_map: dict[int, dict] = {}
    for pr in prs:
        ex_id = pr.exercise_id
        if ex_id not in exercise_map:
            exercise_name = pr.exercise.name if pr.exercise else "Unknown"
            muscle_group = pr.exercise.muscle_group if pr.exercise else None
            exercise_map[ex_id] = {
                "exercise_id": ex_id,
                "exercise_name": exercise_name,
                "muscle_group": muscle_group,
                "best_weight": None,
                "best_reps": None,
                "best_volume": None,
                "latest_date": None,
            }

        record = exercise_map[ex_id]

        if pr.type == "weight":
            record["best_weight"] = pr.value
        elif pr.type == "reps":
            record["best_reps"] = pr.value
        elif pr.type == "volume":
            record["best_volume"] = pr.value

        # Track the most recent achieved_at date
        if pr.achieved_at:
            achieved_str = pr.achieved_at.strftime("%b %d, %Y") if isinstance(pr.achieved_at, datetime) else str(pr.achieved_at)
            if record["latest_date"] is None:
                record["latest_date"] = achieved_str
            else:
                # Keep the most recent date
                if isinstance(pr.achieved_at, datetime):
                    existing_date = record.get("_latest_dt")
                    if existing_date is None or pr.achieved_at > existing_date:
                        record["latest_date"] = achieved_str
                        record["_latest_dt"] = pr.achieved_at

    # Clean up internal tracking keys and return as list
    records = []
    for record in exercise_map.values():
        record.pop("_latest_dt", None)
        records.append(record)

    return records


async def get_recent_prs(
    db: AsyncSession,
    user_id: int,
    days: int = 30,
) -> list[dict]:
    """
    Get personal records achieved in the last N days.
    Returns a list of dicts with exercise_name, type, value, achieved_at.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(PersonalRecord)
        .where(
            and_(
                PersonalRecord.user_id == user_id,
                PersonalRecord.achieved_at >= cutoff,
            )
        )
        .options(selectinload(PersonalRecord.exercise))
        .order_by(PersonalRecord.achieved_at.desc())
    )
    prs = result.scalars().all()

    recent: list[dict] = []
    for pr in prs:
        exercise_name = pr.exercise.name if pr.exercise else "Unknown Exercise"
        achieved_str = ""
        if pr.achieved_at:
            if isinstance(pr.achieved_at, datetime):
                achieved_str = pr.achieved_at.strftime("%b %d, %Y")
            else:
                achieved_str = str(pr.achieved_at)

        recent.append({
            "exercise_id": pr.exercise_id,
            "exercise_name": exercise_name,
            "type": pr.type,
            "value": pr.value,
            "achieved_at": achieved_str,
        })

    return recent


async def get_pr_set_ids_for_workout(
    db: AsyncSession,
    user_id: int,
    workout_id: int,
) -> set[int]:
    """
    Get set IDs in a workout that are current personal records.
    Used to display PR badges on workout detail pages.
    """
    pr_set_ids: set[int] = set()

    # Get workout exercises and sets
    workout_result = await db.execute(
        select(Workout)
        .where(and_(Workout.id == workout_id, Workout.user_id == user_id))
        .options(
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.sets)
        )
    )
    workout = workout_result.scalar_one_or_none()
    if workout is None:
        return pr_set_ids

    # Get all PRs for this user that reference this workout
    pr_result = await db.execute(
        select(PersonalRecord).where(
            and_(
                PersonalRecord.user_id == user_id,
                PersonalRecord.workout_id == workout_id,
            )
        )
    )
    prs = pr_result.scalars().all()

    # Build a map of exercise_id -> set of PR types achieved in this workout
    pr_map: dict[int, set[str]] = {}
    for pr in prs:
        if pr.exercise_id not in pr_map:
            pr_map[pr.exercise_id] = set()
        pr_map[pr.exercise_id].add(pr.type)

    # For each workout exercise that has a PR, find the set that achieved it
    for we in workout.workout_exercises:
        if we.exercise_id not in pr_map:
            continue

        pr_types = pr_map[we.exercise_id]
        sets = we.sets
        if not sets:
            continue

        if "weight" in pr_types:
            best_weight_set = max(sets, key=lambda s: s.weight)
            pr_set_ids.add(best_weight_set.id)

        if "reps" in pr_types:
            best_reps_set = max(sets, key=lambda s: s.reps)
            pr_set_ids.add(best_reps_set.id)

        if "volume" in pr_types:
            best_volume_set = max(sets, key=lambda s: s.weight * s.reps)
            pr_set_ids.add(best_volume_set.id)

    return pr_set_ids


async def get_exercise_prs(
    db: AsyncSession,
    user_id: int,
    exercise_id: int,
) -> list[dict]:
    """
    Get all personal records for a specific exercise.
    Used on exercise detail pages.
    """
    result = await db.execute(
        select(PersonalRecord).where(
            and_(
                PersonalRecord.user_id == user_id,
                PersonalRecord.exercise_id == exercise_id,
            )
        )
        .order_by(PersonalRecord.type)
    )
    prs = result.scalars().all()

    records: list[dict] = []
    for pr in prs:
        achieved_str = ""
        if pr.achieved_at:
            if isinstance(pr.achieved_at, datetime):
                achieved_str = pr.achieved_at.strftime("%b %d, %Y")
            else:
                achieved_str = str(pr.achieved_at)

        records.append({
            "type": pr.type,
            "value": pr.value,
            "achieved_at": achieved_str,
        })

    return records