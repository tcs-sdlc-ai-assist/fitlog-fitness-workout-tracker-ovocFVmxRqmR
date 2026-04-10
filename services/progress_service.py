import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, distinct, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.workout import Workout, WorkoutExercise
from models.exercise import Exercise
from models.set import Set
from models.personal_record import PersonalRecord


async def get_streak_stats(db: AsyncSession, user_id: int) -> dict:
    """Calculate current streak, longest streak, total workouts, and workouts this month."""
    # Total workouts
    total_result = await db.execute(
        select(func.count(Workout.id)).where(Workout.user_id == user_id)
    )
    total_workouts = total_result.scalar() or 0

    # Workouts this month
    today = date.today()
    first_of_month = today.replace(day=1)
    month_result = await db.execute(
        select(func.count(Workout.id)).where(
            and_(
                Workout.user_id == user_id,
                Workout.date >= first_of_month,
                Workout.date <= today,
            )
        )
    )
    workouts_this_month = month_result.scalar() or 0

    # Get all distinct workout dates sorted descending for streak calculation
    dates_result = await db.execute(
        select(distinct(Workout.date))
        .where(Workout.user_id == user_id)
        .order_by(desc(Workout.date))
    )
    workout_dates = sorted([row[0] for row in dates_result.all()], reverse=True)

    current_streak = _calculate_current_streak(workout_dates, today)
    longest_streak = _calculate_longest_streak(workout_dates)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_workouts": total_workouts,
        "workouts_this_month": workouts_this_month,
    }


def _calculate_current_streak(workout_dates: list, today: date) -> int:
    """Calculate the current consecutive day streak ending today or yesterday."""
    if not workout_dates:
        return 0

    streak = 0
    # Allow streak to start from today or yesterday
    check_date = today

    if workout_dates and workout_dates[0] < today - timedelta(days=1):
        return 0

    if workout_dates[0] == today:
        check_date = today
    elif workout_dates[0] == today - timedelta(days=1):
        check_date = today - timedelta(days=1)
    else:
        return 0

    date_set = set(workout_dates)

    while check_date in date_set:
        streak += 1
        check_date -= timedelta(days=1)

    return streak


def _calculate_longest_streak(workout_dates: list) -> int:
    """Calculate the longest consecutive day streak from a sorted list of dates."""
    if not workout_dates:
        return 0

    # Sort ascending for easier processing
    sorted_dates = sorted(set(workout_dates))

    if len(sorted_dates) == 1:
        return 1

    longest = 1
    current = 1

    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


async def get_muscle_group_distribution(db: AsyncSession, user_id: int) -> list:
    """Get aggregated muscle group distribution from all user workouts."""
    # Count sets per muscle group across all workouts
    result = await db.execute(
        select(
            Exercise.muscle_group,
            func.count(Set.id).label("set_count"),
        )
        .select_from(Set)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .where(Workout.user_id == user_id)
        .group_by(Exercise.muscle_group)
        .order_by(desc("set_count"))
    )

    rows = result.all()

    if not rows:
        return []

    total_sets = sum(row.set_count for row in rows)

    distribution = []
    for row in rows:
        percentage = (row.set_count / total_sets * 100) if total_sets > 0 else 0
        distribution.append(
            {
                "muscle_group": row.muscle_group,
                "count": row.set_count,
                "percentage": round(percentage, 1),
            }
        )

    return distribution


async def get_personal_records_summary(db: AsyncSession, user_id: int) -> list:
    """Get all personal records grouped by exercise for the progress page."""
    result = await db.execute(
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(PersonalRecord.user_id == user_id)
        .order_by(PersonalRecord.exercise_id, PersonalRecord.type)
    )
    prs = result.scalars().all()

    # Group by exercise
    exercise_map: dict = {}
    for pr in prs:
        exercise_id = pr.exercise_id
        if exercise_id not in exercise_map:
            exercise_name = pr.exercise.name if pr.exercise else "Unknown"
            muscle_group = pr.exercise.muscle_group if pr.exercise else ""
            exercise_map[exercise_id] = {
                "exercise_id": exercise_id,
                "exercise_name": exercise_name,
                "muscle_group": muscle_group,
                "best_weight": None,
                "best_reps": None,
                "best_volume": None,
                "latest_date": None,
            }

        record = exercise_map[exercise_id]

        if pr.type == "weight":
            record["best_weight"] = pr.value
        elif pr.type == "reps":
            record["best_reps"] = pr.value
        elif pr.type == "volume":
            record["best_volume"] = pr.value

        if pr.achieved_at:
            achieved_date = pr.achieved_at
            if isinstance(achieved_date, datetime):
                achieved_date = achieved_date.date()
            if record["latest_date"] is None:
                record["latest_date"] = achieved_date
            elif achieved_date > record["latest_date"]:
                record["latest_date"] = achieved_date

    records = list(exercise_map.values())

    # Format dates for display
    for record in records:
        if record["latest_date"] is not None:
            if isinstance(record["latest_date"], date):
                record["latest_date"] = record["latest_date"].strftime("%b %d, %Y")

    return records


async def get_recent_prs(
    db: AsyncSession, user_id: int, days: int = 30
) -> list:
    """Get personal records achieved in the last N days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(
            and_(
                PersonalRecord.user_id == user_id,
                PersonalRecord.achieved_at >= cutoff_date,
            )
        )
        .order_by(desc(PersonalRecord.achieved_at))
    )
    prs = result.scalars().all()

    recent = []
    for pr in prs:
        exercise_name = pr.exercise.name if pr.exercise else "Unknown Exercise"
        achieved_at = pr.achieved_at
        if isinstance(achieved_at, datetime):
            achieved_str = achieved_at.strftime("%b %d, %Y")
        elif isinstance(achieved_at, date):
            achieved_str = achieved_at.strftime("%b %d, %Y")
        else:
            achieved_str = str(achieved_at) if achieved_at else ""

        recent.append(
            {
                "exercise_name": exercise_name,
                "type": pr.type,
                "value": pr.value,
                "achieved_at": achieved_str,
                "exercise_id": pr.exercise_id,
            }
        )

    return recent


async def get_workout_consistency(
    db: AsyncSession, user_id: int, weeks: int = 12
) -> list:
    """Get weekly workout counts for the last N weeks."""
    today = date.today()
    start_date = today - timedelta(weeks=weeks)

    result = await db.execute(
        select(Workout.date)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.date >= start_date,
                Workout.date <= today,
            )
        )
        .order_by(Workout.date)
    )
    workout_dates = [row[0] for row in result.all()]

    # Build weekly buckets
    weekly_data = []
    week_start = start_date - timedelta(days=start_date.weekday())  # Monday

    while week_start <= today:
        week_end = week_start + timedelta(days=6)
        count = sum(
            1 for d in workout_dates if week_start <= d <= week_end
        )
        weekly_data.append(
            {
                "week_start": week_start.strftime("%b %d"),
                "week_end": week_end.strftime("%b %d"),
                "count": count,
            }
        )
        week_start += timedelta(weeks=1)

    return weekly_data


async def get_weekly_activity(db: AsyncSession, user_id: int) -> list:
    """Get activity for the current week (Mon-Sun) for the dashboard."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(Workout.date)
        .where(
            and_(
                Workout.user_id == user_id,
                Workout.date >= monday,
                Workout.date <= monday + timedelta(days=6),
            )
        )
    )
    workout_dates_set = set(row[0] for row in result.all())

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekly = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        weekly.append(
            {
                "label": day_labels[i],
                "date_short": day_date.strftime("%d"),
                "date": day_date,
                "has_workout": day_date in workout_dates_set,
            }
        )

    return weekly


async def get_workouts_this_week(db: AsyncSession, user_id: int) -> int:
    """Count workouts logged this week (Mon-Sun)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(func.count(Workout.id)).where(
            and_(
                Workout.user_id == user_id,
                Workout.date >= monday,
                Workout.date <= today,
            )
        )
    )
    return result.scalar() or 0


async def get_total_workouts(db: AsyncSession, user_id: int) -> int:
    """Get total workout count for a user."""
    result = await db.execute(
        select(func.count(Workout.id)).where(Workout.user_id == user_id)
    )
    return result.scalar() or 0