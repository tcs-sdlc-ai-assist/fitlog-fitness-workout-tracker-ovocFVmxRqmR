import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import create_tables, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()

    # Run seed script
    try:
        from seed import run_seed
        await run_seed()
    except Exception as e:
        print(f"Seed script warning: {e}")

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="FitLog Workout Tracker",
    description="A comprehensive workout tracking API built with Python and FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"))
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Import and include routers
from routers.auth import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.exercises import router as exercises_router
from routers.workouts import router as workouts_router
from routers.templates import router as templates_router
from routers.measurements import router as measurements_router
from routers.progress import router as progress_router
from routers.admin import router as admin_router
from routers.profile import router as profile_router

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(exercises_router)
app.include_router(workouts_router)
app.include_router(templates_router)
app.include_router(measurements_router)
app.include_router(progress_router)
app.include_router(admin_router)
app.include_router(profile_router)


@app.get("/health")
async def health_check():
    environment = os.getenv("ENVIRONMENT", "development")
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": environment,
        }
    )


@app.get("/healthz")
async def healthz():
    return JSONResponse(content={"status": "ok"})


@app.get("/")
async def root(request: Request):
    from utils.dependencies import get_optional_user, get_db
    from database import async_session_maker
    from utils.security import COOKIE_NAME, get_user_id_from_token
    from sqlalchemy import select
    from models.user import User

    token = request.cookies.get(COOKIE_NAME)
    if token is not None:
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            async with async_session_maker() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user is not None and user.is_active:
                    if user.role == "admin":
                        from fastapi.responses import RedirectResponse
                        return RedirectResponse(url="/admin/dashboard/", status_code=302)
                    from fastapi.responses import RedirectResponse
                    return RedirectResponse(url="/dashboard/", status_code=302)

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auth/login", status_code=302)


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auth/login", status_code=302)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden"},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"},
    )