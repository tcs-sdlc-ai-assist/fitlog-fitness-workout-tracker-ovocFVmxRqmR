import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.exercise import Exercise
from models.workout import Workout
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from utils.dependencies import get_db, require_admin
from services.exercise_service import (
    search_exercises,
    get_exercise_by_id,
    add_exercise,
    edit_exercise,
    delete_exercise,
    check_exercise_name_exists,
)
from services.template_service import get_system_templates, enrich_template_exercises

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter(prefix="/admin")


async def _get_admin_stats(db: AsyncSession) -> dict:
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    total_workouts_result = await db.execute(select(func.count(Workout.id)))
    total_workouts = total_workouts_result.scalar() or 0

    total_exercises_result = await db.execute(select(func.count(Exercise.id)))
    total_exercises = total_exercises_result.scalar() or 0

    seven_days_ago = date.today() - timedelta(days=7)
    active_users_result = await db.execute(
        select(func.count(func.distinct(Workout.user_id))).where(
            Workout.date >= seven_days_ago
        )
    )
    active_users_7d = active_users_result.scalar() or 0

    return {
        "total_users": total_users,
        "total_workouts": total_workouts,
        "total_exercises": total_exercises,
        "active_users_7d": active_users_7d,
    }


@router.get("/dashboard/")
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    stats = await _get_admin_stats(db)

    exercises_data = await search_exercises(db, page=1, page_size=50)
    exercises = exercises_data["exercises"]

    system_templates_list = await get_system_templates(db)
    enriched_templates = []
    for tmpl in system_templates_list:
        enriched_exercises = enrich_template_exercises(tmpl)
        enriched_templates.append({
            "id": tmpl.id,
            "name": tmpl.name,
            "is_system": tmpl.is_system,
            "created_at": tmpl.created_at,
            "exercises": enriched_exercises,
        })

    users_result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(20)
    )
    users = list(users_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "exercises": exercises,
            "templates": enriched_templates,
            "users": users,
        },
    )


@router.get("/dashboard")
async def admin_dashboard_no_slash(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    return RedirectResponse(url="/admin/dashboard/", status_code=302)


@router.get("/exercises/new")
async def admin_exercise_new_form(
    request: Request,
    user: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        request,
        "admin/exercise_form.html",
        context={
            "user": user,
            "exercise": None,
        },
    )


@router.post("/exercises/create")
async def admin_exercise_create(
    request: Request,
    name: str = Form(...),
    muscle_group: str = Form(...),
    equipment: str = Form(...),
    instructions: str = Form(""),
    is_system: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    name = name.strip()
    muscle_group = muscle_group.strip()
    equipment = equipment.strip()
    instructions = instructions.strip() if instructions else None

    if not name or not muscle_group or not equipment:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": None,
                "error": "Name, muscle group, and equipment are required.",
            },
            status_code=400,
        )

    name_exists = await check_exercise_name_exists(db, name)
    if name_exists:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": None,
                "error": f"An exercise named '{name}' already exists.",
            },
            status_code=400,
        )

    system_flag = is_system.lower() in ("true", "on", "1", "yes") if is_system else False

    await add_exercise(
        db=db,
        name=name,
        muscle_group=muscle_group,
        equipment=equipment,
        instructions=instructions,
        is_system=system_flag,
        created_by=user.id,
    )

    return RedirectResponse(url="/admin/dashboard/", status_code=303)


@router.get("/exercises/{exercise_id}/edit")
async def admin_exercise_edit_form(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    exercise = await get_exercise_by_id(db, exercise_id)
    if exercise is None:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    return templates.TemplateResponse(
        request,
        "admin/exercise_form.html",
        context={
            "user": user,
            "exercise": exercise,
        },
    )


@router.post("/exercises/{exercise_id}/edit")
async def admin_exercise_update(
    request: Request,
    exercise_id: int,
    name: str = Form(...),
    muscle_group: str = Form(...),
    equipment: str = Form(...),
    instructions: str = Form(""),
    is_system: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    exercise = await get_exercise_by_id(db, exercise_id)
    if exercise is None:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    name = name.strip()
    muscle_group = muscle_group.strip()
    equipment = equipment.strip()
    instructions = instructions.strip() if instructions else None

    if not name or not muscle_group or not equipment:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": exercise,
                "error": "Name, muscle group, and equipment are required.",
            },
            status_code=400,
        )

    name_exists = await check_exercise_name_exists(db, name, exclude_id=exercise_id)
    if name_exists:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": exercise,
                "error": f"An exercise named '{name}' already exists.",
            },
            status_code=400,
        )

    system_flag = is_system.lower() in ("true", "on", "1", "yes") if is_system else False

    await edit_exercise(
        db=db,
        exercise_id=exercise_id,
        name=name,
        muscle_group=muscle_group,
        equipment=equipment,
        instructions=instructions,
        is_system=system_flag,
    )

    return RedirectResponse(url="/admin/dashboard/", status_code=303)


@router.post("/exercises/{exercise_id}/delete")
async def admin_exercise_delete(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await delete_exercise(db, exercise_id)
    return RedirectResponse(url="/admin/dashboard/", status_code=303)


@router.get("/users/")
async def admin_users_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    users_result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = list(users_result.scalars().all())

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        context={
            "user": user,
            "stats": await _get_admin_stats(db),
            "exercises": [],
            "templates": [],
            "users": users,
        },
    )


@router.post("/users/{user_id}/activate")
async def admin_user_activate(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user is None:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    if target_user.id == user.id:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    target_user.is_active = True
    await db.flush()

    return RedirectResponse(url="/admin/dashboard/", status_code=303)


@router.post("/users/{user_id}/deactivate")
async def admin_user_deactivate(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user is None:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    if target_user.id == user.id:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    target_user.is_active = False
    await db.flush()

    return RedirectResponse(url="/admin/dashboard/", status_code=303)


@router.post("/users/{user_id}/toggle")
async def admin_user_toggle(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user is None:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    if target_user.id == user.id:
        return RedirectResponse(url="/admin/dashboard/", status_code=302)

    target_user.is_active = not target_user.is_active
    await db.flush()

    return RedirectResponse(url="/admin/dashboard/", status_code=303)