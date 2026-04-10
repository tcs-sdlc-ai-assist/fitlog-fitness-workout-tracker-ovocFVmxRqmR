import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from routers.auth import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.exercises import router as exercises_router
from routers.workouts import router as workouts_router
from routers.templates import router as templates_router
from routers.measurements import router as measurements_router
from routers.progress import router as progress_router
from routers.admin import router as admin_router
from routers.profile import router as profile_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "exercises_router",
    "workouts_router",
    "templates_router",
    "measurements_router",
    "progress_router",
    "admin_router",
    "profile_router",
]