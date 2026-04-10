import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from models.user import User
from utils.dependencies import get_db, get_optional_user, get_current_user
from services.exercise_service import (
    search_exercises,
    get_exercise_by_id,
    get_all_muscle_groups,
    get_all_equipment_types,
    get_exercise_history_for_user,
    get_exercise_prs,
    add_exercise,
    edit_exercise,
    delete_exercise,
    check_exercise_name_exists,
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter()


@router.get("/exercises/")
async def exercise_library(
    request: Request,
    q: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    result = await search_exercises(
        db=db,
        query=q,
        muscle_group=muscle_group,
        equipment=equipment,
        page=page,
        page_size=page_size,
    )

    muscle_groups = await get_all_muscle_groups(db)
    equipment_types = await get_all_equipment_types(db)

    return templates.TemplateResponse(
        request,
        "exercises/library.html",
        context={
            "user": user,
            "exercises": result["exercises"],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
            "search_query": q,
            "selected_muscle_group": muscle_group,
            "selected_equipment": equipment,
            "muscle_groups": muscle_groups,
            "equipment_types": equipment_types,
        },
    )


@router.get("/exercises/new")
async def new_exercise_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/exercises/", status_code=303)

    return templates.TemplateResponse(
        request,
        "admin/exercise_form.html",
        context={
            "user": user,
            "exercise": None,
        },
    )


@router.post("/exercises/new")
async def create_exercise(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url="/exercises/", status_code=303)

    form = await request.form()
    name = form.get("name", "").strip()
    muscle_group_val = form.get("muscle_group", "").strip()
    equipment_val = form.get("equipment", "").strip()
    instructions = form.get("instructions", "").strip() or None
    is_system = form.get("is_system") == "true"

    errors = []
    if not name:
        errors.append("Exercise name is required.")
    if not muscle_group_val:
        errors.append("Muscle group is required.")
    if not equipment_val:
        errors.append("Equipment is required.")

    if name and await check_exercise_name_exists(db, name):
        errors.append(f"An exercise named '{name}' already exists.")

    if errors:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": None,
                "error": " ".join(errors),
            },
        )

    exercise = await add_exercise(
        db=db,
        name=name,
        muscle_group=muscle_group_val,
        equipment=equipment_val,
        instructions=instructions,
        is_system=is_system,
        created_by=user.id,
    )

    return RedirectResponse(url=f"/exercises/{exercise.id}", status_code=303)


@router.get("/exercises/{exercise_id}")
async def exercise_detail(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    exercise = await get_exercise_by_id(db, exercise_id)
    if exercise is None:
        return templates.TemplateResponse(
            request,
            "exercises/library.html",
            context={
                "user": user,
                "exercises": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
                "search_query": None,
                "selected_muscle_group": None,
                "selected_equipment": None,
                "muscle_groups": [],
                "equipment_types": [],
                "error": "Exercise not found.",
            },
            status_code=404,
        )

    history = []
    personal_records = []

    if user is not None:
        history = await get_exercise_history_for_user(
            db=db,
            exercise_id=exercise_id,
            user_id=user.id,
            limit=20,
        )
        personal_records = await get_exercise_prs(
            db=db,
            exercise_id=exercise_id,
            user_id=user.id,
        )

    return templates.TemplateResponse(
        request,
        "exercises/detail.html",
        context={
            "user": user,
            "exercise": exercise,
            "history": history,
            "personal_records": personal_records,
        },
    )


@router.get("/exercises/{exercise_id}/edit")
async def edit_exercise_form(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url=f"/exercises/{exercise_id}", status_code=303)

    exercise = await get_exercise_by_id(db, exercise_id)
    if exercise is None:
        return RedirectResponse(url="/exercises/", status_code=303)

    return templates.TemplateResponse(
        request,
        "admin/exercise_form.html",
        context={
            "user": user,
            "exercise": exercise,
        },
    )


@router.post("/exercises/{exercise_id}/edit")
async def update_exercise(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url=f"/exercises/{exercise_id}", status_code=303)

    exercise = await get_exercise_by_id(db, exercise_id)
    if exercise is None:
        return RedirectResponse(url="/exercises/", status_code=303)

    form = await request.form()
    name = form.get("name", "").strip()
    muscle_group_val = form.get("muscle_group", "").strip()
    equipment_val = form.get("equipment", "").strip()
    instructions = form.get("instructions", "").strip() or None
    is_system = form.get("is_system") == "true"

    errors = []
    if not name:
        errors.append("Exercise name is required.")
    if not muscle_group_val:
        errors.append("Muscle group is required.")
    if not equipment_val:
        errors.append("Equipment is required.")

    if name and await check_exercise_name_exists(db, name, exclude_id=exercise_id):
        errors.append(f"An exercise named '{name}' already exists.")

    if errors:
        return templates.TemplateResponse(
            request,
            "admin/exercise_form.html",
            context={
                "user": user,
                "exercise": exercise,
                "error": " ".join(errors),
            },
        )

    updated = await edit_exercise(
        db=db,
        exercise_id=exercise_id,
        name=name,
        muscle_group=muscle_group_val,
        equipment=equipment_val,
        instructions=instructions,
        is_system=is_system,
    )

    return RedirectResponse(url=f"/exercises/{exercise_id}", status_code=303)


@router.post("/exercises/{exercise_id}/delete")
async def remove_exercise(
    request: Request,
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        return RedirectResponse(url=f"/exercises/{exercise_id}", status_code=303)

    deleted = await delete_exercise(db, exercise_id)

    if deleted:
        return RedirectResponse(url="/exercises/", status_code=303)
    else:
        return RedirectResponse(url="/exercises/", status_code=303)