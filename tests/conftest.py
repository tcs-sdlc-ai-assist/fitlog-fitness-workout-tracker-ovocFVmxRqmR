import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from typing import AsyncGenerator, Optional

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database import Base
from models.user import User
from models.exercise import Exercise
from models.workout import Workout, WorkoutExercise
from models.set import Set
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from models.body_measurement import BodyMeasurement
from models.personal_record import PersonalRecord
from utils.security import hash_password, create_access_token, COOKIE_NAME


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

test_async_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db dependency to use the test database."""
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with the test database dependency override."""
    from main import app
    from utils.dependencies import get_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard test user."""
    user = User(
        display_name="Test User",
        email="testuser@example.com",
        username="testuser",
        password_hash=hash_password("TestPass123"),
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    admin = User(
        display_name="Test Admin",
        email="testadmin@example.com",
        username="testadmin",
        password_hash=hash_password("AdminPass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive test user."""
    user = User(
        display_name="Inactive User",
        email="inactive@example.com",
        username="inactiveuser",
        password_hash=hash_password("InactivePass123"),
        role="user",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


def make_auth_cookie(user: User) -> dict[str, str]:
    """Generate an authentication cookie dict for a given user."""
    token = create_access_token(data={"sub": str(user.id)})
    return {COOKIE_NAME: token}


@pytest_asyncio.fixture
async def auth_cookies_user(test_user: User) -> dict[str, str]:
    """Return auth cookies for the standard test user."""
    return make_auth_cookie(test_user)


@pytest_asyncio.fixture
async def auth_cookies_admin(test_admin: User) -> dict[str, str]:
    """Return auth cookies for the admin test user."""
    return make_auth_cookie(test_admin)


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, auth_cookies_user: dict[str, str]) -> AsyncClient:
    """Return a test client with user authentication cookies set."""
    client.cookies.update(auth_cookies_user)
    return client


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, auth_cookies_admin: dict[str, str]) -> AsyncClient:
    """Return a test client with admin authentication cookies set."""
    client.cookies.update(auth_cookies_admin)
    return client


@pytest_asyncio.fixture
async def sample_exercise(db_session: AsyncSession) -> Exercise:
    """Create a sample exercise for testing."""
    exercise = Exercise(
        name="Test Bench Press",
        muscle_group="Chest",
        equipment="Barbell",
        instructions="Lie on a flat bench and press the barbell upward.",
        is_system=True,
        created_by=None,
    )
    db_session.add(exercise)
    await db_session.flush()
    await db_session.refresh(exercise)
    return exercise


@pytest_asyncio.fixture
async def sample_exercises(db_session: AsyncSession) -> list[Exercise]:
    """Create multiple sample exercises for testing."""
    exercises_data = [
        {
            "name": "Test Squat",
            "muscle_group": "Legs",
            "equipment": "Barbell",
            "instructions": "Stand with barbell on upper back and squat down.",
            "is_system": True,
        },
        {
            "name": "Test Pull-Up",
            "muscle_group": "Back",
            "equipment": "Bodyweight",
            "instructions": "Hang from a bar and pull yourself up.",
            "is_system": True,
        },
        {
            "name": "Test Overhead Press",
            "muscle_group": "Shoulders",
            "equipment": "Barbell",
            "instructions": "Press the barbell overhead from shoulder height.",
            "is_system": True,
        },
    ]
    exercises = []
    for ex_data in exercises_data:
        exercise = Exercise(**ex_data, created_by=None)
        db_session.add(exercise)
        await db_session.flush()
        await db_session.refresh(exercise)
        exercises.append(exercise)
    return exercises


@pytest_asyncio.fixture
async def sample_workout(db_session: AsyncSession, test_user: User, sample_exercise: Exercise) -> Workout:
    """Create a sample workout with one exercise and two sets."""
    from datetime import date, datetime, timezone

    workout = Workout(
        user_id=test_user.id,
        date=date.today(),
        duration_minutes=45,
        notes="Test workout session",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(workout)
    await db_session.flush()

    workout_exercise = WorkoutExercise(
        workout_id=workout.id,
        exercise_id=sample_exercise.id,
        order_index=0,
    )
    db_session.add(workout_exercise)
    await db_session.flush()

    set1 = Set(
        workout_exercise_id=workout_exercise.id,
        weight=135.0,
        reps=10,
        order_index=0,
        is_pr=False,
    )
    set2 = Set(
        workout_exercise_id=workout_exercise.id,
        weight=155.0,
        reps=8,
        order_index=1,
        is_pr=False,
    )
    db_session.add(set1)
    db_session.add(set2)
    await db_session.flush()

    await db_session.refresh(workout)
    return workout


@pytest_asyncio.fixture
async def sample_template(db_session: AsyncSession, test_user: User, sample_exercise: Exercise) -> WorkoutTemplate:
    """Create a sample workout template."""
    template = WorkoutTemplate(
        user_id=test_user.id,
        name="Test Template",
        description="A test workout template",
        is_system=False,
    )
    db_session.add(template)
    await db_session.flush()

    template_exercise = TemplateExercise(
        template_id=template.id,
        exercise_id=sample_exercise.id,
        order_index=0,
        sets_count=3,
        default_reps=10,
        default_weight=None,
    )
    db_session.add(template_exercise)
    await db_session.flush()

    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def sample_measurement(db_session: AsyncSession, test_user: User) -> BodyMeasurement:
    """Create a sample body measurement."""
    from datetime import date

    measurement = BodyMeasurement(
        user_id=test_user.id,
        measurement_date=date.today(),
        weight=175.5,
        body_fat_percent=18.0,
        chest=42.0,
        waist=34.0,
        hips=None,
        arms=15.0,
        thighs=24.0,
    )
    db_session.add(measurement)
    await db_session.flush()
    await db_session.refresh(measurement)
    return measurement