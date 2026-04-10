import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.exercise import Exercise
from models.personal_record import PersonalRecord
from models.set import Set
from models.workout import Workout, WorkoutExercise
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from schemas.workout import (
    PRUpdate,
    SetCreate,
    WorkoutCreate,
    WorkoutCreateResponse,
    WorkoutDetailResponse,
    WorkoutExerciseCreate,
    WorkoutExerciseDetailResponse,
    WorkoutListResponse,
    WorkoutResponse,
    WorkoutUpdate,
    SetResponse,
)


async def log_workout(
    db: AsyncSession,
    user_id: int,
    data: WorkoutCreate,
) -> WorkoutCreateResponse:
    workout = Workout(
        user_id=user_id,
        date=data.date,
        duration_minutes=data.duration_minutes,
        notes=data.notes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(workout)
    await db.flush()

    pr_updates: list[PRUpdate] = []

    for ex_idx, exercise_data in enumerate(data.exercises):
        workout_exercise = WorkoutExercise(
            workout_id=workout.id,
            exercise_id=exercise_data.exercise_id,
            order_index=exercise_data.order_index if exercise_data.order_index else ex_idx,
        )
        db.add(workout_exercise)
        await db.flush()

        for set_idx, set_data in enumerate(exercise_data.sets):
            workout_set = Set(
                workout_exercise_id=workout_exercise.id,
                weight=set_data.weight,
                reps=set_data.reps,
                order_index=set_data.order_index if set_data.order_index else set_idx,
                is_pr=False,
            )
            db.add(workout_set)

        await db.flush()

        exercise_prs = await _detect_and_update_prs(
            db=db,
            user_id=user_id,
            exercise_id=exercise_data.exercise_id,
            workout_id=workout.id,
            sets=exercise_data.sets,
            workout_date=data.date,
        )
        pr_updates.extend(exercise_prs)

    if data.save_as_template and data.template_name:
        await _save_workout_as_template(
            db=db,
            user_id=user_id,
            template_name=data.template_name,
            exercises=data.exercises,
        )

    await db.flush()

    return WorkoutCreateResponse(
        workout_id=workout.id,
        pr_updates=pr_updates,
    )


async def get_workout_history(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> WorkoutListResponse:
    count_query = select(func.count(Workout.id)).where(Workout.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    query = (
        select(Workout)
        .where(Workout.user_id == user_id)
        .order_by(Workout.date.desc(), Workout.id.desc())
        .offset(offset)
        .limit(page_size)
        .options(selectinload(Workout.workout_exercises))
    )
    result = await db.execute(query)
    workouts = result.scalars().all()

    workout_responses: list[WorkoutResponse] = []
    for w in workouts:
        workout_responses.append(
            WorkoutResponse(
                id=w.id,
                user_id=w.user_id,
                date=w.date,
                duration_minutes=w.duration_minutes,
                notes=w.notes,
                created_at=w.created_at,
            )
        )

    return WorkoutListResponse(
        workouts=workout_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_workout_detail(
    db: AsyncSession,
    workout_id: int,
    user_id: int,
) -> Optional[WorkoutDetailResponse]:
    query = (
        select(Workout)
        .where(Workout.id == workout_id, Workout.user_id == user_id)
        .options(
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.sets),
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.exercise),
        )
    )
    result = await db.execute(query)
    workout = result.scalar_one_or_none()

    if workout is None:
        return None

    exercises_detail: list[WorkoutExerciseDetailResponse] = []
    for we in workout.workout_exercises:
        sets_response: list[SetResponse] = []
        if we.sets:
            for s in sorted(we.sets, key=lambda x: x.order_index):
                sets_response.append(
                    SetResponse(
                        id=s.id,
                        workout_exercise_id=s.workout_exercise_id,
                        weight=s.weight,
                        reps=s.reps,
                        order_index=s.order_index,
                    )
                )

        exercise_name = None
        muscle_group = None
        if we.exercise:
            exercise_name = we.exercise.name
            muscle_group = we.exercise.muscle_group

        exercises_detail.append(
            WorkoutExerciseDetailResponse(
                id=we.id,
                workout_id=we.workout_id,
                exercise_id=we.exercise_id,
                order_index=we.order_index,
                sets=sets_response,
                exercise_name=exercise_name,
                muscle_group=muscle_group,
            )
        )

    exercises_detail.sort(key=lambda x: x.order_index)

    return WorkoutDetailResponse(
        id=workout.id,
        user_id=workout.user_id,
        date=workout.date,
        duration_minutes=workout.duration_minutes,
        notes=workout.notes,
        created_at=workout.created_at,
        exercises=exercises_detail,
    )


async def edit_workout(
    db: AsyncSession,
    workout_id: int,
    user_id: int,
    data: WorkoutUpdate,
) -> Optional[WorkoutDetailResponse]:
    query = select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()

    if workout is None:
        return None

    if data.date is not None:
        workout.date = data.date
    if data.duration_minutes is not None:
        workout.duration_minutes = data.duration_minutes
    if data.notes is not None:
        workout.notes = data.notes

    if data.exercises is not None:
        existing_we_query = select(WorkoutExercise).where(
            WorkoutExercise.workout_id == workout_id
        )
        existing_we_result = await db.execute(existing_we_query)
        existing_wes = existing_we_result.scalars().all()

        for existing_we in existing_wes:
            await db.execute(
                delete(Set).where(Set.workout_exercise_id == existing_we.id)
            )
        await db.execute(
            delete(WorkoutExercise).where(WorkoutExercise.workout_id == workout_id)
        )
        await db.flush()

        for ex_idx, exercise_data in enumerate(data.exercises):
            workout_exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=exercise_data.exercise_id,
                order_index=exercise_data.order_index if exercise_data.order_index else ex_idx,
            )
            db.add(workout_exercise)
            await db.flush()

            for set_idx, set_data in enumerate(exercise_data.sets):
                workout_set = Set(
                    workout_exercise_id=workout_exercise.id,
                    weight=set_data.weight,
                    reps=set_data.reps,
                    order_index=set_data.order_index if set_data.order_index else set_idx,
                    is_pr=False,
                )
                db.add(workout_set)

        await db.flush()

    await db.flush()

    return await get_workout_detail(db, workout_id, user_id)


async def delete_workout(
    db: AsyncSession,
    workout_id: int,
    user_id: int,
) -> bool:
    query = select(Workout).where(Workout.id == workout_id, Workout.user_id == user_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()

    if workout is None:
        return False

    we_query = select(WorkoutExercise).where(WorkoutExercise.workout_id == workout_id)
    we_result = await db.execute(we_query)
    workout_exercises = we_result.scalars().all()

    for we in workout_exercises:
        await db.execute(delete(Set).where(Set.workout_exercise_id == we.id))

    await db.execute(
        delete(WorkoutExercise).where(WorkoutExercise.workout_id == workout_id)
    )

    await db.execute(
        delete(PersonalRecord).where(PersonalRecord.workout_id == workout_id)
    )

    await db.delete(workout)
    await db.flush()

    return True


async def get_weekly_activity(
    db: AsyncSession,
    user_id: int,
    reference_date: Optional[date] = None,
) -> list[dict[str, Any]]:
    if reference_date is None:
        reference_date = date.today()

    monday = reference_date - timedelta(days=reference_date.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    start_date = week_dates[0]
    end_date = week_dates[-1]

    query = (
        select(Workout.date)
        .where(
            Workout.user_id == user_id,
            Workout.date >= start_date,
            Workout.date <= end_date,
        )
    )
    result = await db.execute(query)
    workout_dates = {row[0] for row in result.all()}

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekly_activity: list[dict[str, Any]] = []

    for i, d in enumerate(week_dates):
        weekly_activity.append({
            "label": day_labels[i],
            "date": d,
            "date_short": d.strftime("%d"),
            "has_workout": d in workout_dates,
        })

    return weekly_activity


async def get_workout_stats(
    db: AsyncSession,
    user_id: int,
) -> dict[str, Any]:
    total_query = select(func.count(Workout.id)).where(Workout.user_id == user_id)
    total_result = await db.execute(total_query)
    total_workouts = total_result.scalar() or 0

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_query = select(func.count(Workout.id)).where(
        Workout.user_id == user_id,
        Workout.date >= monday,
        Workout.date <= today,
    )
    week_result = await db.execute(week_query)
    workouts_this_week = week_result.scalar() or 0

    current_streak = await _calculate_current_streak(db, user_id)

    return {
        "total_workouts": total_workouts,
        "workouts_this_week": workouts_this_week,
        "current_streak": current_streak,
    }


async def get_recent_workouts(
    db: AsyncSession,
    user_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    query = (
        select(Workout)
        .where(Workout.user_id == user_id)
        .order_by(Workout.date.desc(), Workout.id.desc())
        .limit(limit)
        .options(selectinload(Workout.workout_exercises))
    )
    result = await db.execute(query)
    workouts = result.scalars().all()

    recent: list[dict[str, Any]] = []
    for w in workouts:
        exercise_count = len(w.workout_exercises) if w.workout_exercises else 0
        recent.append({
            "id": w.id,
            "date": w.date,
            "duration_minutes": w.duration_minutes,
            "notes": w.notes,
            "exercise_count": exercise_count,
        })

    return recent


async def get_workouts_for_calendar(
    db: AsyncSession,
    user_id: int,
    year: int,
    month: int,
) -> list[dict[str, Any]]:
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    start_offset = first_day.weekday()
    cal_start = first_day - timedelta(days=start_offset)

    days_after = 6 - last_day.weekday()
    cal_end = last_day + timedelta(days=days_after)

    query = (
        select(Workout)
        .where(
            Workout.user_id == user_id,
            Workout.date >= cal_start,
            Workout.date <= cal_end,
        )
        .options(selectinload(Workout.workout_exercises))
    )
    result = await db.execute(query)
    workouts = result.scalars().all()

    workout_map: dict[date, list[Any]] = {}
    for w in workouts:
        if w.date not in workout_map:
            workout_map[w.date] = []
        workout_map[w.date].append(w)

    calendar_days: list[dict[str, Any]] = []
    current = cal_start
    while current <= cal_end:
        day_workouts = workout_map.get(current, [])
        has_workout = len(day_workouts) > 0
        workout_id = day_workouts[0].id if has_workout else None
        workout_count = len(day_workouts)

        workout_summary = ""
        if has_workout and day_workouts[0].workout_exercises:
            exercise_count = len(day_workouts[0].workout_exercises)
            workout_summary = f"{exercise_count} exercise{'s' if exercise_count != 1 else ''}"

        calendar_days.append({
            "date": current,
            "date_str": current.isoformat(),
            "day_number": current.day,
            "in_current_month": current.month == month,
            "is_today": current == date.today(),
            "has_workout": has_workout,
            "workout_id": workout_id,
            "workout_count": workout_count,
            "workout_summary": workout_summary,
        })
        current += timedelta(days=1)

    return calendar_days


async def get_workout_exercise_count(
    db: AsyncSession,
    workout_id: int,
) -> int:
    query = select(func.count(WorkoutExercise.id)).where(
        WorkoutExercise.workout_id == workout_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def get_workout_total_volume(
    db: AsyncSession,
    workout_id: int,
) -> float:
    query = (
        select(func.sum(Set.weight * Set.reps))
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .where(WorkoutExercise.workout_id == workout_id)
    )
    result = await db.execute(query)
    return result.scalar() or 0.0


async def get_workouts_with_stats(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    count_query = select(func.count(Workout.id)).where(Workout.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    query = (
        select(Workout)
        .where(Workout.user_id == user_id)
        .order_by(Workout.date.desc(), Workout.id.desc())
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.sets),
        )
    )
    result = await db.execute(query)
    workouts = result.scalars().all()

    workout_list: list[dict[str, Any]] = []
    for w in workouts:
        exercise_count = len(w.workout_exercises) if w.workout_exercises else 0
        total_volume = 0.0
        if w.workout_exercises:
            for we in w.workout_exercises:
                if we.sets:
                    for s in we.sets:
                        total_volume += s.weight * s.reps

        workout_list.append({
            "id": w.id,
            "user_id": w.user_id,
            "date": w.date,
            "duration_minutes": w.duration_minutes,
            "notes": w.notes,
            "created_at": w.created_at,
            "exercise_count": exercise_count,
            "total_volume": total_volume,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "workouts": workout_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def _detect_and_update_prs(
    db: AsyncSession,
    user_id: int,
    exercise_id: int,
    workout_id: int,
    sets: list[SetCreate],
    workout_date: date,
) -> list[PRUpdate]:
    pr_updates: list[PRUpdate] = []

    if not sets:
        return pr_updates

    max_weight = max(s.weight for s in sets)
    max_reps = max(s.reps for s in sets)
    total_volume = sum(s.weight * s.reps for s in sets)

    pr_checks = [
        ("weight", max_weight),
        ("reps", float(max_reps)),
        ("volume", total_volume),
    ]

    for pr_type, new_value in pr_checks:
        existing_pr_query = select(PersonalRecord).where(
            PersonalRecord.user_id == user_id,
            PersonalRecord.exercise_id == exercise_id,
            PersonalRecord.type == pr_type,
        )
        existing_pr_result = await db.execute(existing_pr_query)
        existing_pr = existing_pr_result.scalar_one_or_none()

        if existing_pr is None:
            new_pr = PersonalRecord(
                user_id=user_id,
                exercise_id=exercise_id,
                type=pr_type,
                value=new_value,
                workout_id=workout_id,
                achieved_at=datetime.combine(workout_date, datetime.min.time()),
            )
            db.add(new_pr)
            pr_updates.append(
                PRUpdate(exercise_id=exercise_id, type=pr_type, new_value=new_value)
            )
        elif new_value > existing_pr.value:
            existing_pr.value = new_value
            existing_pr.workout_id = workout_id
            existing_pr.achieved_at = datetime.combine(workout_date, datetime.min.time())
            pr_updates.append(
                PRUpdate(exercise_id=exercise_id, type=pr_type, new_value=new_value)
            )

    await db.flush()
    return pr_updates


async def _save_workout_as_template(
    db: AsyncSession,
    user_id: int,
    template_name: str,
    exercises: list[WorkoutExerciseCreate],
) -> WorkoutTemplate:
    template = WorkoutTemplate(
        user_id=user_id,
        name=template_name,
        is_system=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(template)
    await db.flush()

    for idx, exercise_data in enumerate(exercises):
        template_exercise = TemplateExercise(
            template_id=template.id,
            exercise_id=exercise_data.exercise_id,
            order_index=exercise_data.order_index if exercise_data.order_index else idx,
        )
        db.add(template_exercise)

    await db.flush()
    return template


async def _calculate_current_streak(
    db: AsyncSession,
    user_id: int,
) -> int:
    query = (
        select(Workout.date)
        .where(Workout.user_id == user_id)
        .distinct()
        .order_by(Workout.date.desc())
    )
    result = await db.execute(query)
    workout_dates = [row[0] for row in result.all()]

    if not workout_dates:
        return 0

    today = date.today()
    streak = 0

    if workout_dates[0] == today:
        check_date = today
    elif workout_dates[0] == today - timedelta(days=1):
        check_date = today - timedelta(days=1)
    else:
        return 0

    workout_date_set = set(workout_dates)

    while check_date in workout_date_set:
        streak += 1
        check_date -= timedelta(days=1)

    return streak


async def calculate_longest_streak(
    db: AsyncSession,
    user_id: int,
) -> int:
    query = (
        select(Workout.date)
        .where(Workout.user_id == user_id)
        .distinct()
        .order_by(Workout.date.asc())
    )
    result = await db.execute(query)
    workout_dates = [row[0] for row in result.all()]

    if not workout_dates:
        return 0

    longest = 1
    current = 1

    for i in range(1, len(workout_dates)):
        if workout_dates[i] == workout_dates[i - 1] + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


async def get_workouts_this_month(
    db: AsyncSession,
    user_id: int,
) -> int:
    today = date.today()
    first_of_month = date(today.year, today.month, 1)
    query = select(func.count(Workout.id)).where(
        Workout.user_id == user_id,
        Workout.date >= first_of_month,
        Workout.date <= today,
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def get_total_exercises_logged(
    db: AsyncSession,
    user_id: int,
) -> int:
    query = (
        select(func.count(WorkoutExercise.id))
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .where(Workout.user_id == user_id)
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def get_exercise_history(
    db: AsyncSession,
    user_id: int,
    exercise_id: int,
    limit: int = 20,
) -> list[dict[str, Any]]:
    query = (
        select(
            Workout.id.label("workout_id"),
            Workout.date,
            Set.weight,
            Set.reps,
            Set.order_index,
        )
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .join(Set, Set.workout_exercise_id == WorkoutExercise.id)
        .where(
            Workout.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
        )
        .order_by(Workout.date.desc(), Set.order_index.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    history: list[dict[str, Any]] = []
    for row in rows:
        history.append({
            "workout_id": row.workout_id,
            "date": row.date,
            "weight": row.weight,
            "reps": row.reps,
            "set_number": row.order_index + 1,
        })

    return history


async def get_muscle_group_distribution(
    db: AsyncSession,
    user_id: int,
) -> list[dict[str, Any]]:
    query = (
        select(
            Exercise.muscle_group,
            func.count(Set.id).label("set_count"),
        )
        .join(WorkoutExercise, WorkoutExercise.exercise_id == Exercise.id)
        .join(Set, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .where(Workout.user_id == user_id)
        .group_by(Exercise.muscle_group)
        .order_by(func.count(Set.id).desc())
    )
    result = await db.execute(query)
    rows = result.all()

    total_sets = sum(row.set_count for row in rows) if rows else 0

    distribution: list[dict[str, Any]] = []
    for row in rows:
        percentage = (row.set_count / total_sets * 100) if total_sets > 0 else 0
        distribution.append({
            "muscle_group": row.muscle_group,
            "count": row.set_count,
            "percentage": round(percentage, 1),
        })

    return distribution


async def get_pr_set_ids_for_workout(
    db: AsyncSession,
    workout_id: int,
    user_id: int,
) -> set[int]:
    query = select(PersonalRecord.workout_id).where(
        PersonalRecord.user_id == user_id,
        PersonalRecord.workout_id == workout_id,
    )
    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return set()

    we_query = (
        select(Set.id)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .where(WorkoutExercise.workout_id == workout_id)
    )

    pr_exercise_query = select(PersonalRecord.exercise_id).where(
        PersonalRecord.user_id == user_id,
        PersonalRecord.workout_id == workout_id,
    )
    pr_exercise_result = await db.execute(pr_exercise_query)
    pr_exercise_ids = {row[0] for row in pr_exercise_result.all()}

    best_set_query = (
        select(Set.id)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .where(
            WorkoutExercise.workout_id == workout_id,
            WorkoutExercise.exercise_id.in_(pr_exercise_ids),
        )
        .order_by(Set.weight.desc())
    )
    best_set_result = await db.execute(best_set_query)
    all_set_ids = [row[0] for row in best_set_result.all()]

    pr_set_ids: set[int] = set()
    seen_exercises: set[int] = set()

    set_exercise_query = (
        select(Set.id, WorkoutExercise.exercise_id, Set.weight)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .where(
            WorkoutExercise.workout_id == workout_id,
            WorkoutExercise.exercise_id.in_(pr_exercise_ids),
        )
        .order_by(Set.weight.desc())
    )
    set_exercise_result = await db.execute(set_exercise_query)
    set_exercise_rows = set_exercise_result.all()

    for row in set_exercise_rows:
        set_id, ex_id, weight = row
        if ex_id not in seen_exercises:
            pr_set_ids.add(set_id)
            seen_exercises.add(ex_id)

    return pr_set_ids