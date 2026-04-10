import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from services.measurement_service import (
    delete_measurement,
    edit_measurement,
    get_measurement_by_id,
    get_measurement_history,
    get_trend_summary,
    log_measurement,
)
from utils.dependencies import get_current_user, get_db

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/measurements/")
async def measurements_list(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    history_data = await get_measurement_history(
        db=db,
        user_id=user.id,
        page=page,
        page_size=page_size,
    )

    trend_data = await get_trend_summary(db=db, user_id=user.id, days=30)

    weight_trend = trend_data.get("weight_trend", {})
    body_fat_trend = trend_data.get("body_fat_trend", {})
    waist_trend = trend_data.get("waist_trend", {})

    return templates.TemplateResponse(
        request,
        "measurements/list.html",
        context={
            "user": user,
            "measurements": history_data["measurements"],
            "total": history_data["total"],
            "page": history_data["page"],
            "page_size": history_data["page_size"],
            "total_pages": history_data["total_pages"],
            "weight_trend": weight_trend,
            "body_fat_trend": body_fat_trend,
            "waist_trend": waist_trend,
        },
    )


@router.get("/measurements/new")
async def measurements_new_form(
    request: Request,
    user: User = Depends(get_current_user),
):
    today_str = date.today().isoformat()

    return templates.TemplateResponse(
        request,
        "measurements/form.html",
        context={
            "user": user,
            "editing": False,
            "measurement": None,
            "today": today_str,
            "prefill_date": today_str,
        },
    )


@router.post("/measurements/new")
async def measurements_create(
    request: Request,
    measurement_date: str = Form(...),
    weight: Optional[str] = Form(None),
    body_fat_percent: Optional[str] = Form(None),
    chest: Optional[str] = Form(None),
    waist: Optional[str] = Form(None),
    hips: Optional[str] = Form(None),
    arms: Optional[str] = Form(None),
    thighs: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        parsed_date = date.fromisoformat(measurement_date.strip())
    except (ValueError, AttributeError):
        return templates.TemplateResponse(
            request,
            "measurements/form.html",
            context={
                "user": user,
                "editing": False,
                "measurement": None,
                "today": date.today().isoformat(),
                "prefill_date": measurement_date,
                "error": "Invalid date format.",
            },
            status_code=422,
        )

    weight_val = _parse_optional_float(weight)
    body_fat_val = _parse_optional_float(body_fat_percent)
    chest_val = _parse_optional_float(chest)
    waist_val = _parse_optional_float(waist)
    hips_val = _parse_optional_float(hips)
    arms_val = _parse_optional_float(arms)
    thighs_val = _parse_optional_float(thighs)

    has_any_value = any(
        v is not None
        for v in [weight_val, body_fat_val, chest_val, waist_val, hips_val, arms_val, thighs_val]
    )
    if not has_any_value:
        return templates.TemplateResponse(
            request,
            "measurements/form.html",
            context={
                "user": user,
                "editing": False,
                "measurement": None,
                "today": date.today().isoformat(),
                "prefill_date": measurement_date,
                "error": "Please enter at least one measurement value.",
            },
            status_code=422,
        )

    try:
        await log_measurement(
            db=db,
            user_id=user.id,
            measurement_date=parsed_date,
            weight=weight_val,
            body_fat_percent=body_fat_val,
            chest=chest_val,
            waist=waist_val,
            hips=hips_val,
            arms=arms_val,
            thighs=thighs_val,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "measurements/form.html",
            context={
                "user": user,
                "editing": False,
                "measurement": None,
                "today": date.today().isoformat(),
                "prefill_date": measurement_date,
                "error": str(e),
            },
            status_code=409,
        )

    return RedirectResponse(url="/measurements/", status_code=303)


@router.get("/measurements/{measurement_id}/edit")
async def measurements_edit_form(
    request: Request,
    measurement_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    measurement = await get_measurement_by_id(
        db=db,
        measurement_id=measurement_id,
        user_id=user.id,
    )

    if measurement is None:
        return RedirectResponse(url="/measurements/", status_code=303)

    return templates.TemplateResponse(
        request,
        "measurements/form.html",
        context={
            "user": user,
            "editing": True,
            "measurement": measurement,
            "today": date.today().isoformat(),
        },
    )


@router.post("/measurements/{measurement_id}/edit")
async def measurements_update(
    request: Request,
    measurement_id: int,
    measurement_date: str = Form(...),
    weight: Optional[str] = Form(None),
    body_fat_percent: Optional[str] = Form(None),
    chest: Optional[str] = Form(None),
    waist: Optional[str] = Form(None),
    hips: Optional[str] = Form(None),
    arms: Optional[str] = Form(None),
    thighs: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await get_measurement_by_id(
        db=db,
        measurement_id=measurement_id,
        user_id=user.id,
    )
    if existing is None:
        return RedirectResponse(url="/measurements/", status_code=303)

    try:
        parsed_date = date.fromisoformat(measurement_date.strip())
    except (ValueError, AttributeError):
        return templates.TemplateResponse(
            request,
            "measurements/form.html",
            context={
                "user": user,
                "editing": True,
                "measurement": existing,
                "today": date.today().isoformat(),
                "error": "Invalid date format.",
            },
            status_code=422,
        )

    weight_val = _parse_optional_float(weight)
    body_fat_val = _parse_optional_float(body_fat_percent)
    chest_val = _parse_optional_float(chest)
    waist_val = _parse_optional_float(waist)
    hips_val = _parse_optional_float(hips)
    arms_val = _parse_optional_float(arms)
    thighs_val = _parse_optional_float(thighs)

    try:
        await edit_measurement(
            db=db,
            measurement_id=measurement_id,
            user_id=user.id,
            measurement_date=parsed_date,
            weight=weight_val,
            body_fat_percent=body_fat_val,
            chest=chest_val,
            waist=waist_val,
            hips=hips_val,
            arms=arms_val,
            thighs=thighs_val,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "measurements/form.html",
            context={
                "user": user,
                "editing": True,
                "measurement": existing,
                "today": date.today().isoformat(),
                "error": str(e),
            },
            status_code=409,
        )

    return RedirectResponse(url="/measurements/", status_code=303)


@router.post("/measurements/{measurement_id}/delete")
async def measurements_delete(
    request: Request,
    measurement_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await delete_measurement(
        db=db,
        measurement_id=measurement_id,
        user_id=user.id,
    )

    return RedirectResponse(url="/measurements/", status_code=303)


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    try:
        parsed = float(stripped)
        if parsed <= 0:
            return None
        return parsed
    except (ValueError, TypeError):
        return None