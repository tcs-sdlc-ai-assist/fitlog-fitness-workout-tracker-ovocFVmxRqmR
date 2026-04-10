import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from utils.dependencies import get_db, get_optional_user
from utils.security import (
    COOKIE_NAME,
    COOKIE_HTTPONLY,
    COOKIE_MAX_AGE,
    COOKIE_PATH,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
)
from services.auth_service import register_user, login_user
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/login")
async def login_page(
    request: Request,
    user: User = Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard/", status_code=302)
        return RedirectResponse(url="/dashboard/", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/login.html",
        context={
            "user": None,
            "error": None,
            "form_data": None,
        },
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    token = await login_user(db, username, password)

    if token is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Invalid username or password.",
                "form_data": {"username": username},
            },
            status_code=400,
        )

    from services.auth_service import get_current_user as get_user_from_token

    user = await get_user_from_token(db, token)

    if user is None:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            context={
                "user": None,
                "error": "Authentication failed. Please try again.",
                "form_data": {"username": username},
            },
            status_code=400,
        )

    if user.role == "admin":
        redirect_url = "/admin/dashboard/"
    else:
        redirect_url = "/dashboard/"

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
    )
    return response


@router.get("/register")
async def register_page(
    request: Request,
    user: User = Depends(get_optional_user),
):
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/admin/dashboard/", status_code=302)
        return RedirectResponse(url="/dashboard/", status_code=302)

    return templates.TemplateResponse(
        request,
        "auth/register.html",
        context={
            "user": None,
            "errors": None,
            "form_data": None,
        },
    )


@router.post("/register")
async def register_submit(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    errors = []

    display_name_stripped = display_name.strip()
    if not display_name_stripped:
        errors.append("Display name is required.")
    elif len(display_name_stripped) > 100:
        errors.append("Display name must be 100 characters or fewer.")

    email_stripped = email.strip()
    if not email_stripped:
        errors.append("Email is required.")

    username_stripped = username.strip().lower()
    if not username_stripped:
        errors.append("Username is required.")
    elif len(username_stripped) < 3:
        errors.append("Username must be at least 3 characters.")
    elif len(username_stripped) > 50:
        errors.append("Username must be 50 characters or fewer.")
    elif not all(c.isalnum() or c in ("_", "-") for c in username_stripped):
        errors.append("Username may only contain letters, numbers, hyphens, and underscores.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif len(password) > 128:
        errors.append("Password must be 128 characters or fewer.")

    if password != confirm_password:
        errors.append("Passwords do not match.")

    form_data = {
        "display_name": display_name,
        "email": email,
        "username": username,
    }

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=400,
        )

    try:
        await register_user(
            db=db,
            display_name=display_name_stripped,
            email=email_stripped,
            username=username_stripped,
            password=password,
        )
    except ValueError as e:
        errors.append(str(e))
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=400,
        )
    except Exception:
        errors.append("An unexpected error occurred. Please try again.")
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            context={
                "user": None,
                "errors": errors,
                "form_data": form_data,
            },
            status_code=500,
        )

    return RedirectResponse(url="/auth/login", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    return response