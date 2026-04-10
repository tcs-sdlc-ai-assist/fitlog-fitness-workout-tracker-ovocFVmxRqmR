import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from utils.dependencies import get_db, get_current_user
from models.user import User
from services.auth_service import update_user_profile
from services.workout_service import get_total_workouts, get_total_exercises_logged

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter()


@router.get("/profile/")
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_workouts = await get_total_workouts(db, user.id)
    total_exercises_logged = await get_total_exercises_logged(db, user.id)

    return templates.TemplateResponse(
        request,
        "profile/index.html",
        context={
            "user": user,
            "profile_user": user,
            "total_workouts": total_workouts,
            "total_exercises_logged": total_exercises_logged,
        },
    )


@router.post("/profile/update")
async def profile_update(
    request: Request,
    display_name: str = Form(""),
    email: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    display_name_val = display_name.strip() if display_name else None
    email_val = email.strip() if email else None

    if not display_name_val and not email_val:
        total_workouts = await get_total_workouts(db, user.id)
        total_exercises_logged = await get_total_exercises_logged(db, user.id)
        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "profile_user": user,
                "total_workouts": total_workouts,
                "total_exercises_logged": total_exercises_logged,
                "error": "Please provide at least one field to update.",
            },
        )

    try:
        updated_user = await update_user_profile(
            db=db,
            user=user,
            display_name=display_name_val,
            email=email_val,
        )

        total_workouts = await get_total_workouts(db, user.id)
        total_exercises_logged = await get_total_exercises_logged(db, user.id)

        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": updated_user,
                "profile_user": updated_user,
                "total_workouts": total_workouts,
                "total_exercises_logged": total_exercises_logged,
                "success": "Profile updated successfully.",
            },
        )
    except ValueError as e:
        total_workouts = await get_total_workouts(db, user.id)
        total_exercises_logged = await get_total_exercises_logged(db, user.id)

        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "profile_user": user,
                "total_workouts": total_workouts,
                "total_exercises_logged": total_exercises_logged,
                "error": str(e),
            },
        )
    except Exception:
        total_workouts = await get_total_workouts(db, user.id)
        total_exercises_logged = await get_total_exercises_logged(db, user.id)

        return templates.TemplateResponse(
            request,
            "profile/index.html",
            context={
                "user": user,
                "profile_user": user,
                "total_workouts": total_workouts,
                "total_exercises_logged": total_exercises_logged,
                "error": "An unexpected error occurred. Please try again.",
            },
        )