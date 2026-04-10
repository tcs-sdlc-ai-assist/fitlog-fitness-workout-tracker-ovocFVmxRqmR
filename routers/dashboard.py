import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from utils.dependencies import get_db, get_current_user
from models.user import User
from services.workout_service import (
    get_recent_workouts,
    get_weekly_activity,
    get_workout_stats,
)
from services.progress_service import get_recent_prs
from services.measurement_service import get_current_weight

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/dashboard/")
async def dashboard_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Render the user dashboard with summary cards, weekly activity, recent workouts, and PR highlights."""

    # Get workout stats (total, this week, current streak)
    workout_stats = await get_workout_stats(db, user.id)

    # Get weekly activity grid (Mon-Sun)
    weekly_activity = await get_weekly_activity(db, user.id)

    # Get recent workouts (last 5)
    recent_workouts = await get_recent_workouts(db, user.id, limit=5)

    # Get recent personal records (last 30 days)
    recent_prs = await get_recent_prs(db, user.id, days=30)

    # Get current body weight
    current_weight = await get_current_weight(db, user.id)

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        context={
            "user": user,
            "workouts_this_week": workout_stats.get("workouts_this_week", 0),
            "current_streak": workout_stats.get("current_streak", 0),
            "total_workouts": workout_stats.get("total_workouts", 0),
            "current_weight": current_weight,
            "weekly_activity": weekly_activity,
            "recent_workouts": recent_workouts,
            "recent_prs": recent_prs,
        },
    )


@router.get("/dashboard")
async def dashboard_redirect() -> RedirectResponse:
    """Redirect /dashboard to /dashboard/ for consistency."""
    return RedirectResponse(url="/dashboard/", status_code=301)