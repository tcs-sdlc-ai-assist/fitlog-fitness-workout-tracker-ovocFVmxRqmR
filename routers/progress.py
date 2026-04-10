import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from utils.dependencies import get_db, get_current_user
from services.progress_service import (
    get_streak_stats,
    get_muscle_group_distribution,
    get_personal_records_summary,
    get_recent_prs,
)

router = APIRouter(prefix="/progress", tags=["progress"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/", response_class=HTMLResponse)
async def progress_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    streak_stats = await get_streak_stats(db, user.id)
    muscle_group_distribution = await get_muscle_group_distribution(db, user.id)
    personal_records = await get_personal_records_summary(db, user.id)
    recent_prs = await get_recent_prs(db, user.id, days=30)

    return templates.TemplateResponse(
        request,
        "progress/index.html",
        context={
            "user": user,
            "streak_stats": streak_stats,
            "muscle_group_distribution": muscle_group_distribution,
            "personal_records": personal_records,
            "recent_prs": recent_prs,
        },
    )