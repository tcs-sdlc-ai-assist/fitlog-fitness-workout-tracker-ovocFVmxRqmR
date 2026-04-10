import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calendar as cal_module
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.dependencies import get_current_user, get_db
from services.workout_service import (
    log_workout,
    get_workout_detail,
    get_workouts_with_stats,
    edit_workout,
    delete_workout,
    get_workouts_for_calendar,
    get_pr_set_ids_for_workout,
)
from services.exercise_service import get_all_exercises
from services.template_service import (
    get_all_templates_for_user,
    get_template_detail,
    enrich_template_exercises,
)
from schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutExerciseCreate,
    SetCreate,
)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


def _parse_exercises_from_form(form_data: dict) -> list[dict]:
    """Parse the dynamic exercise/set form fields into structured data."""
    exercises_map: dict[int, dict] = {}

    for key, value in form_data.items():
        if not key.startswith("exercises["):
            continue

        parts = key.replace("]", "").split("[")
        if len(parts) < 3:
            continue

        try:
            ex_idx = int(parts[1])
        except (ValueError, IndexError):
            continue

        if ex_idx not in exercises_map:
            exercises_map[ex_idx] = {"exercise_id": None, "sets": {}}

        field_name = parts[2]

        if field_name == "exercise_id":
            try:
                exercises_map[ex_idx]["exercise_id"] = int(value)
            except (ValueError, TypeError):
                pass
        elif field_name == "sets" and len(parts) >= 4:
            try:
                set_idx = int(parts[3])
            except (ValueError, IndexError):
                continue

            if set_idx not in exercises_map[ex_idx]["sets"]:
                exercises_map[ex_idx]["sets"][set_idx] = {"weight": None, "reps": None}

            if len(parts) >= 5:
                set_field = parts[4]
                if set_field == "weight":
                    try:
                        exercises_map[ex_idx]["sets"][set_idx]["weight"] = float(value)
                    except (ValueError, TypeError):
                        pass
                elif set_field == "reps":
                    try:
                        exercises_map[ex_idx]["sets"][set_idx]["reps"] = int(value)
                    except (ValueError, TypeError):
                        pass

    result = []
    for ex_idx in sorted(exercises_map.keys()):
        ex_data = exercises_map[ex_idx]
        if ex_data["exercise_id"] is None:
            continue

        sets_list = []
        for set_idx in sorted(ex_data["sets"].keys()):
            s = ex_data["sets"][set_idx]
            if s["weight"] is not None and s["reps"] is not None:
                sets_list.append({
                    "weight": s["weight"],
                    "reps": s["reps"],
                    "order_index": set_idx,
                })

        if sets_list:
            result.append({
                "exercise_id": ex_data["exercise_id"],
                "order_index": ex_idx,
                "sets": sets_list,
            })

    return result


@router.get("/workouts/")
async def workout_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    view: str = "list",
    page: int = 1,
    page_size: int = 20,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    today = date.today()

    if view == "calendar":
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        year = max(2000, min(2100, year))
        month = max(1, min(12, month))

        calendar_days = await get_workouts_for_calendar(db, user.id, year, month)
        month_name = cal_module.month_name[month]

        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year = year - 1

        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year = year + 1

        from services.workout_service import get_workout_stats
        stats = await get_workout_stats(db, user.id)
        total = stats["total_workouts"]

        return templates.TemplateResponse(
            request,
            "workouts/history.html",
            context={
                "user": user,
                "view": "calendar",
                "calendar_days": calendar_days,
                "year": year,
                "month": month,
                "month_name": month_name,
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_year": next_year,
                "next_month": next_month,
                "total": total,
                "total_pages": 1,
                "page": 1,
                "page_size": page_size,
                "workouts": [],
            },
        )
    else:
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        result = await get_workouts_with_stats(db, user.id, page=page, page_size=page_size)

        return templates.TemplateResponse(
            request,
            "workouts/history.html",
            context={
                "user": user,
                "view": "list",
                "workouts": result["workouts"],
                "total": result["total"],
                "page": result["page"],
                "page_size": result["page_size"],
                "total_pages": result["total_pages"],
                "calendar_days": [],
                "year": None,
                "month": None,
                "month_name": "",
                "prev_year": None,
                "prev_month": None,
                "next_year": None,
                "next_month": None,
            },
        )


@router.get("/workouts/new")
async def new_workout_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    template_id: Optional[int] = None,
    date_param: Optional[str] = None,
):
    exercises = await get_all_exercises(db)
    all_templates = await get_all_templates_for_user(db, user.id)

    prefill_date = date.today().isoformat()
    if date_param:
        try:
            date.fromisoformat(date_param)
            prefill_date = date_param
        except ValueError:
            pass

    # Check query param "date" as well
    query_date = request.query_params.get("date")
    if query_date:
        try:
            date.fromisoformat(query_date)
            prefill_date = query_date
        except ValueError:
            pass

    workout_exercises = []
    if template_id is not None:
        template = await get_template_detail(db, template_id)
        if template is not None:
            enriched = enrich_template_exercises(template)
            for te in enriched:
                workout_exercises.append({
                    "exercise_id": te["exercise_id"],
                    "order_index": te["order_index"],
                    "sets": [
                        {"weight": te.get("default_weight") or "", "reps": te.get("default_reps") or 10}
                        for _ in range(te.get("sets_count") or 3)
                    ],
                })

    return templates.TemplateResponse(
        request,
        "workouts/form.html",
        context={
            "user": user,
            "editing": False,
            "workout": None,
            "workout_exercises": workout_exercises if workout_exercises else None,
            "exercises": exercises,
            "templates_available": all_templates,
            "today": date.today().isoformat(),
            "prefill_date": prefill_date,
        },
    )


@router.post("/workouts/new")
async def create_workout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    form_data = dict(form)

    workout_date_str = form_data.get("date", "")
    duration_str = form_data.get("duration_minutes", "")
    notes = form_data.get("notes", "")
    save_as_template = form_data.get("save_as_template") == "true"
    template_name = form_data.get("template_name", "")

    try:
        workout_date = date.fromisoformat(str(workout_date_str))
    except (ValueError, TypeError):
        exercises = await get_all_exercises(db)
        all_templates = await get_all_templates_for_user(db, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": False,
                "workout": None,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": all_templates,
                "today": date.today().isoformat(),
                "prefill_date": date.today().isoformat(),
                "error": "Invalid date format.",
            },
        )

    duration_minutes = None
    if duration_str:
        try:
            duration_minutes = int(duration_str)
            if duration_minutes <= 0:
                duration_minutes = None
        except (ValueError, TypeError):
            pass

    parsed_exercises = _parse_exercises_from_form(form_data)

    if not parsed_exercises:
        exercises = await get_all_exercises(db)
        all_templates = await get_all_templates_for_user(db, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": False,
                "workout": None,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": all_templates,
                "today": date.today().isoformat(),
                "prefill_date": str(workout_date),
                "error": "At least one exercise with sets is required.",
            },
        )

    exercise_creates = []
    for ex in parsed_exercises:
        set_creates = [
            SetCreate(
                weight=s["weight"],
                reps=s["reps"],
                order_index=s["order_index"],
            )
            for s in ex["sets"]
        ]
        exercise_creates.append(
            WorkoutExerciseCreate(
                exercise_id=ex["exercise_id"],
                order_index=ex["order_index"],
                sets=set_creates,
            )
        )

    workout_data = WorkoutCreate(
        date=workout_date,
        duration_minutes=duration_minutes,
        notes=notes.strip() if notes and notes.strip() else None,
        exercises=exercise_creates,
        save_as_template=save_as_template,
        template_name=template_name.strip() if template_name and template_name.strip() else None,
    )

    try:
        result = await log_workout(db, user.id, workout_data)
    except Exception as e:
        exercises = await get_all_exercises(db)
        all_templates = await get_all_templates_for_user(db, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": False,
                "workout": None,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": all_templates,
                "today": date.today().isoformat(),
                "prefill_date": str(workout_date),
                "error": f"Failed to save workout: {str(e)}",
            },
        )

    return RedirectResponse(
        url=f"/workouts/{result.workout_id}",
        status_code=303,
    )


@router.get("/workouts/{workout_id}")
async def workout_detail_page(
    request: Request,
    workout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workout = await get_workout_detail(db, workout_id, user.id)

    if workout is None:
        return templates.TemplateResponse(
            request,
            "workouts/history.html",
            context={
                "user": user,
                "view": "list",
                "workouts": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
                "calendar_days": [],
                "year": None,
                "month": None,
                "month_name": "",
                "prev_year": None,
                "prev_month": None,
                "next_year": None,
                "next_month": None,
                "error": "Workout not found.",
            },
            status_code=404,
        )

    pr_set_ids = await get_pr_set_ids_for_workout(db, workout_id, user.id)

    exercises = workout.exercises if workout.exercises else []

    total_exercises = len(exercises)
    total_sets = 0
    total_volume = 0.0
    for ex in exercises:
        if ex.sets:
            total_sets += len(ex.sets)
            for s in ex.sets:
                total_volume += s.weight * s.reps

    return templates.TemplateResponse(
        request,
        "workouts/detail.html",
        context={
            "user": user,
            "workout": workout,
            "exercises": exercises,
            "total_exercises": total_exercises,
            "total_sets": total_sets,
            "total_volume": total_volume,
            "pr_set_ids": pr_set_ids,
        },
    )


@router.get("/workouts/{workout_id}/edit")
async def edit_workout_form(
    request: Request,
    workout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    workout = await get_workout_detail(db, workout_id, user.id)

    if workout is None:
        return RedirectResponse(url="/workouts/", status_code=303)

    exercises = await get_all_exercises(db)

    workout_exercises = []
    if workout.exercises:
        for we in workout.exercises:
            sets_data = []
            if we.sets:
                for s in we.sets:
                    sets_data.append({
                        "weight": s.weight,
                        "reps": s.reps,
                        "order_index": s.order_index,
                    })
            workout_exercises.append({
                "exercise_id": we.exercise_id,
                "order_index": we.order_index,
                "sets": sets_data,
            })

    return templates.TemplateResponse(
        request,
        "workouts/form.html",
        context={
            "user": user,
            "editing": True,
            "workout": workout,
            "workout_exercises": workout_exercises,
            "exercises": exercises,
            "templates_available": None,
            "today": date.today().isoformat(),
            "prefill_date": str(workout.date) if workout.date else date.today().isoformat(),
        },
    )


@router.post("/workouts/{workout_id}/edit")
async def update_workout(
    request: Request,
    workout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    form = await request.form()
    form_data = dict(form)

    workout_date_str = form_data.get("date", "")
    duration_str = form_data.get("duration_minutes", "")
    notes = form_data.get("notes", "")

    try:
        workout_date = date.fromisoformat(str(workout_date_str))
    except (ValueError, TypeError):
        exercises = await get_all_exercises(db)
        existing_workout = await get_workout_detail(db, workout_id, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": True,
                "workout": existing_workout,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": None,
                "today": date.today().isoformat(),
                "prefill_date": date.today().isoformat(),
                "error": "Invalid date format.",
            },
        )

    duration_minutes = None
    if duration_str:
        try:
            duration_minutes = int(duration_str)
            if duration_minutes <= 0:
                duration_minutes = None
        except (ValueError, TypeError):
            pass

    parsed_exercises = _parse_exercises_from_form(form_data)

    if not parsed_exercises:
        exercises = await get_all_exercises(db)
        existing_workout = await get_workout_detail(db, workout_id, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": True,
                "workout": existing_workout,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": None,
                "today": date.today().isoformat(),
                "prefill_date": str(workout_date),
                "error": "At least one exercise with sets is required.",
            },
        )

    exercise_creates = []
    for ex in parsed_exercises:
        set_creates = [
            SetCreate(
                weight=s["weight"],
                reps=s["reps"],
                order_index=s["order_index"],
            )
            for s in ex["sets"]
        ]
        exercise_creates.append(
            WorkoutExerciseCreate(
                exercise_id=ex["exercise_id"],
                order_index=ex["order_index"],
                sets=set_creates,
            )
        )

    update_data = WorkoutUpdate(
        date=workout_date,
        duration_minutes=duration_minutes,
        notes=notes.strip() if notes and notes.strip() else None,
        exercises=exercise_creates,
    )

    try:
        result = await edit_workout(db, workout_id, user.id, update_data)
    except Exception as e:
        exercises = await get_all_exercises(db)
        existing_workout = await get_workout_detail(db, workout_id, user.id)
        return templates.TemplateResponse(
            request,
            "workouts/form.html",
            context={
                "user": user,
                "editing": True,
                "workout": existing_workout,
                "workout_exercises": None,
                "exercises": exercises,
                "templates_available": None,
                "today": date.today().isoformat(),
                "prefill_date": str(workout_date),
                "error": f"Failed to update workout: {str(e)}",
            },
        )

    if result is None:
        return RedirectResponse(url="/workouts/", status_code=303)

    return RedirectResponse(
        url=f"/workouts/{workout_id}",
        status_code=303,
    )


@router.post("/workouts/{workout_id}/delete")
async def delete_workout_handler(
    request: Request,
    workout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await delete_workout(db, workout_id, user.id)
    return RedirectResponse(url="/workouts/", status_code=303)