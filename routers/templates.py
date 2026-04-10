import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from models.user import User
from utils.dependencies import get_db, get_current_user
from services.template_service import (
    create_template,
    clone_template,
    edit_template,
    delete_template,
    get_user_templates,
    get_system_templates,
    get_template_detail,
    enrich_template_exercises,
)
from services.exercise_service import get_all_exercises

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


@router.get("/templates/")
async def templates_list_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    my_templates = await get_user_templates(db, user.id)
    system_tmpl = await get_system_templates(db)

    my_templates_enriched = []
    for t in my_templates:
        exercises = enrich_template_exercises(t)
        my_templates_enriched.append({
            "id": t.id,
            "name": t.name,
            "user_id": t.user_id,
            "is_system": t.is_system,
            "created_at": t.created_at,
            "exercises": exercises,
        })

    system_templates_enriched = []
    for t in system_tmpl:
        exercises = enrich_template_exercises(t)
        system_templates_enriched.append({
            "id": t.id,
            "name": t.name,
            "user_id": t.user_id,
            "is_system": t.is_system,
            "created_at": t.created_at,
            "exercises": exercises,
        })

    return templates.TemplateResponse(
        request,
        "templates_dir/list.html",
        context={
            "user": user,
            "my_templates": my_templates_enriched,
            "system_templates": system_templates_enriched,
        },
    )


@router.get("/templates/new")
async def template_new_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exercises = await get_all_exercises(db)

    return templates.TemplateResponse(
        request,
        "templates_dir/form.html",
        context={
            "user": user,
            "template": None,
            "exercises": exercises,
        },
    )


@router.post("/templates/new")
async def template_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
):
    form_data = await request.form()

    exercise_entries = []
    idx = 0
    while True:
        exercise_id_key = f"template_exercises[{idx}][exercise_id]"
        order_index_key = f"template_exercises[{idx}][order_index]"
        exercise_id_val = form_data.get(exercise_id_key)
        if exercise_id_val is None:
            break
        try:
            exercise_id_int = int(exercise_id_val)
        except (ValueError, TypeError):
            idx += 1
            continue
        order_index_val = form_data.get(order_index_key, str(idx))
        try:
            order_index_int = int(order_index_val)
        except (ValueError, TypeError):
            order_index_int = idx
        exercise_entries.append({
            "exercise_id": exercise_id_int,
            "order_index": order_index_int,
        })
        idx += 1

    if not name or not name.strip():
        exercises = await get_all_exercises(db)
        return templates.TemplateResponse(
            request,
            "templates_dir/form.html",
            context={
                "user": user,
                "template": None,
                "exercises": exercises,
                "error": "Template name is required.",
            },
        )

    if not exercise_entries:
        exercises = await get_all_exercises(db)
        return templates.TemplateResponse(
            request,
            "templates_dir/form.html",
            context={
                "user": user,
                "template": None,
                "exercises": exercises,
                "error": "At least one exercise is required.",
            },
        )

    new_template = await create_template(
        db=db,
        user_id=user.id,
        name=name.strip(),
        is_system=False,
        exercises=exercise_entries,
    )

    return RedirectResponse(
        url=f"/templates/{new_template.id}",
        status_code=303,
    )


@router.get("/templates/{template_id}")
async def template_detail_page(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = await get_template_detail(db, template_id)

    if template is None:
        return RedirectResponse(url="/templates/", status_code=303)

    exercises = enrich_template_exercises(template)
    is_owner = template.user_id == user.id

    return templates.TemplateResponse(
        request,
        "templates_dir/detail.html",
        context={
            "user": user,
            "template": template,
            "exercises": exercises,
            "is_owner": is_owner,
        },
    )


@router.get("/templates/{template_id}/edit")
async def template_edit_form(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = await get_template_detail(db, template_id)

    if template is None:
        return RedirectResponse(url="/templates/", status_code=303)

    if template.user_id != user.id:
        return RedirectResponse(url="/templates/", status_code=303)

    exercises = await get_all_exercises(db)
    enriched_exercises = enrich_template_exercises(template)

    template_data = {
        "id": template.id,
        "name": template.name,
        "user_id": template.user_id,
        "is_system": template.is_system,
        "created_at": template.created_at,
        "exercises": enriched_exercises,
    }

    return templates.TemplateResponse(
        request,
        "templates_dir/form.html",
        context={
            "user": user,
            "template": template_data,
            "exercises": exercises,
        },
    )


@router.post("/templates/{template_id}/edit")
async def template_update(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    name: str = Form(...),
):
    form_data = await request.form()

    exercise_entries = []
    idx = 0
    while True:
        exercise_id_key = f"template_exercises[{idx}][exercise_id]"
        order_index_key = f"template_exercises[{idx}][order_index]"
        exercise_id_val = form_data.get(exercise_id_key)
        if exercise_id_val is None:
            break
        try:
            exercise_id_int = int(exercise_id_val)
        except (ValueError, TypeError):
            idx += 1
            continue
        order_index_val = form_data.get(order_index_key, str(idx))
        try:
            order_index_int = int(order_index_val)
        except (ValueError, TypeError):
            order_index_int = idx
        exercise_entries.append({
            "exercise_id": exercise_id_int,
            "order_index": order_index_int,
        })
        idx += 1

    if not name or not name.strip():
        template = await get_template_detail(db, template_id)
        all_exercises = await get_all_exercises(db)
        enriched = enrich_template_exercises(template) if template else []
        template_data = None
        if template:
            template_data = {
                "id": template.id,
                "name": template.name,
                "user_id": template.user_id,
                "is_system": template.is_system,
                "created_at": template.created_at,
                "exercises": enriched,
            }
        return templates.TemplateResponse(
            request,
            "templates_dir/form.html",
            context={
                "user": user,
                "template": template_data,
                "exercises": all_exercises,
                "error": "Template name is required.",
            },
        )

    updated_template = await edit_template(
        db=db,
        template_id=template_id,
        user_id=user.id,
        name=name.strip(),
        exercises=exercise_entries if exercise_entries else None,
    )

    if updated_template is None:
        return RedirectResponse(url="/templates/", status_code=303)

    return RedirectResponse(
        url=f"/templates/{template_id}",
        status_code=303,
    )


@router.post("/templates/{template_id}/delete")
async def template_delete(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = await delete_template(db, template_id, user.id)

    return RedirectResponse(url="/templates/", status_code=303)


@router.post("/templates/{template_id}/clone")
async def template_clone(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cloned = await clone_template(db, template_id, user.id)

    if cloned is None:
        return RedirectResponse(url="/templates/", status_code=303)

    return RedirectResponse(
        url=f"/templates/{cloned.id}",
        status_code=303,
    )