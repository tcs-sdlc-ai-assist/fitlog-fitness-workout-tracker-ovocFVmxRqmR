import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.exercise import Exercise
from models.workout import Workout, WorkoutExercise
from models.set import Set
from models.personal_record import PersonalRecord
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from tests.conftest import make_auth_cookie, override_get_db, test_async_session_maker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _workout_form_data(
    workout_date: str,
    exercises: list[dict],
    duration_minutes: Optional[str] = None,
    notes: Optional[str] = None,
    save_as_template: bool = False,
    template_name: Optional[str] = None,
) -> dict:
    """Build a flat form-data dict matching the workout form structure."""
    data: dict[str, str] = {"date": workout_date}
    if duration_minutes is not None:
        data["duration_minutes"] = duration_minutes
    if notes is not None:
        data["notes"] = notes
    if save_as_template:
        data["save_as_template"] = "true"
    if template_name is not None:
        data["template_name"] = template_name

    for ex_idx, ex in enumerate(exercises):
        data[f"exercises[{ex_idx}][exercise_id]"] = str(ex["exercise_id"])
        for set_idx, s in enumerate(ex.get("sets", [])):
            data[f"exercises[{ex_idx}][sets][{set_idx}][weight]"] = str(s["weight"])
            data[f"exercises[{ex_idx}][sets][{set_idx}][reps]"] = str(s["reps"])

    return data


# ---------------------------------------------------------------------------
# Tests – Create Workout
# ---------------------------------------------------------------------------


class TestCreateWorkout:
    """Tests for POST /workouts/new."""

    @pytest.mark.asyncio
    async def test_create_workout_redirects_to_detail(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [
                        {"weight": 135, "reps": 10},
                        {"weight": 155, "reps": 8},
                    ],
                }
            ],
            duration_minutes="45",
            notes="Great session",
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303
        assert resp.headers["location"].startswith("/workouts/")

    @pytest.mark.asyncio
    async def test_create_workout_persists_data(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        today = date.today().isoformat()
        form = _workout_form_data(
            workout_date=today,
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 100, "reps": 12}],
                }
            ],
            duration_minutes="30",
            notes="Quick workout",
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303

        # Verify in DB
        async with test_async_session_maker() as session:
            result = await session.execute(
                select(Workout).where(Workout.user_id == test_user.id)
            )
            workouts = result.scalars().all()
            assert len(workouts) >= 1
            workout = workouts[-1]
            assert str(workout.date) == today
            assert workout.duration_minutes == 30
            assert workout.notes == "Quick workout"

    @pytest.mark.asyncio
    async def test_create_workout_with_multiple_exercises(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        sample_exercises: list[Exercise],
        test_user: User,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 135, "reps": 10}],
                },
                {
                    "exercise_id": sample_exercises[0].id,
                    "sets": [
                        {"weight": 225, "reps": 5},
                        {"weight": 245, "reps": 3},
                    ],
                },
            ],
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            result = await session.execute(
                select(Workout).where(Workout.user_id == test_user.id)
            )
            workout = result.scalars().all()[-1]

            we_result = await session.execute(
                select(WorkoutExercise).where(WorkoutExercise.workout_id == workout.id)
            )
            workout_exercises = we_result.scalars().all()
            assert len(workout_exercises) == 2

    @pytest.mark.asyncio
    async def test_create_workout_no_exercises_shows_error(
        self,
        authenticated_client: AsyncClient,
    ):
        form = {"date": date.today().isoformat()}
        resp = await authenticated_client.post("/workouts/new", data=form)
        # Should re-render the form (200) with an error message
        assert resp.status_code == 200
        assert b"At least one exercise" in resp.content or b"error" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_create_workout_invalid_date_shows_error(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        form = _workout_form_data(
            workout_date="not-a-date",
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 100, "reps": 10}],
                }
            ],
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 200
        assert b"Invalid date" in resp.content or b"error" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_create_workout_requires_auth(
        self,
        client: AsyncClient,
        sample_exercise: Exercise,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 100, "reps": 10}],
                }
            ],
        )
        resp = await client.post("/workouts/new", data=form)
        # Should redirect to login or return 401
        assert resp.status_code in (302, 303, 401)


# ---------------------------------------------------------------------------
# Tests – Workout History (List & Calendar)
# ---------------------------------------------------------------------------


class TestWorkoutHistory:
    """Tests for GET /workouts/."""

    @pytest.mark.asyncio
    async def test_workout_history_list_view(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        resp = await authenticated_client.get("/workouts/?view=list")
        assert resp.status_code == 200
        assert b"Workout History" in resp.content

    @pytest.mark.asyncio
    async def test_workout_history_calendar_view(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        today = date.today()
        resp = await authenticated_client.get(
            f"/workouts/?view=calendar&year={today.year}&month={today.month}"
        )
        assert resp.status_code == 200
        assert b"Calendar" in resp.content or b"calendar" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_workout_history_empty(
        self,
        authenticated_client: AsyncClient,
    ):
        resp = await authenticated_client.get("/workouts/?view=list")
        assert resp.status_code == 200
        assert b"No workouts" in resp.content or b"no workouts" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_workout_history_requires_auth(
        self,
        client: AsyncClient,
    ):
        resp = await client.get("/workouts/")
        assert resp.status_code in (302, 303, 401)

    @pytest.mark.asyncio
    async def test_workout_history_pagination(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        resp = await authenticated_client.get("/workouts/?view=list&page=1&page_size=5")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests – Workout Detail
# ---------------------------------------------------------------------------


class TestWorkoutDetail:
    """Tests for GET /workouts/{workout_id}."""

    @pytest.mark.asyncio
    async def test_workout_detail_renders(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        resp = await authenticated_client.get(f"/workouts/{sample_workout.id}")
        assert resp.status_code == 200
        assert b"Workout Detail" in resp.content or b"Workout on" in resp.content

    @pytest.mark.asyncio
    async def test_workout_detail_shows_exercises_and_sets(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
        sample_exercise: Exercise,
    ):
        resp = await authenticated_client.get(f"/workouts/{sample_workout.id}")
        assert resp.status_code == 200
        assert sample_exercise.name.encode() in resp.content
        # Should show weight values from the sample workout (135, 155)
        assert b"135" in resp.content
        assert b"155" in resp.content

    @pytest.mark.asyncio
    async def test_workout_detail_not_found(
        self,
        authenticated_client: AsyncClient,
    ):
        resp = await authenticated_client.get("/workouts/99999")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert b"not found" in resp.content.lower() or b"Workout not found" in resp.content

    @pytest.mark.asyncio
    async def test_workout_detail_other_user_not_visible(
        self,
        client: AsyncClient,
        sample_workout: Workout,
        db_session: AsyncSession,
    ):
        """A different user should not see another user's workout."""
        other_user = User(
            display_name="Other User",
            email="other@example.com",
            username="otheruser",
            password_hash="$2b$12$dummyhash",
            role="user",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()
        await db_session.refresh(other_user)

        cookies = make_auth_cookie(other_user)
        client.cookies.update(cookies)

        resp = await client.get(f"/workouts/{sample_workout.id}")
        # Should return 404 or show "not found"
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert b"not found" in resp.content.lower() or b"Workout not found" in resp.content


# ---------------------------------------------------------------------------
# Tests – Edit Workout
# ---------------------------------------------------------------------------


class TestEditWorkout:
    """Tests for GET/POST /workouts/{workout_id}/edit."""

    @pytest.mark.asyncio
    async def test_edit_workout_form_renders(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        resp = await authenticated_client.get(f"/workouts/{sample_workout.id}/edit")
        assert resp.status_code == 200
        assert b"Edit Workout" in resp.content

    @pytest.mark.asyncio
    async def test_edit_workout_updates_data(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
        sample_exercise: Exercise,
        test_user: User,
    ):
        new_date = (date.today() - timedelta(days=1)).isoformat()
        form = _workout_form_data(
            workout_date=new_date,
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 200, "reps": 5}],
                }
            ],
            duration_minutes="60",
            notes="Updated notes",
        )
        resp = await authenticated_client.post(
            f"/workouts/{sample_workout.id}/edit", data=form
        )
        assert resp.status_code == 303

        # Verify update in DB
        async with test_async_session_maker() as session:
            result = await session.execute(
                select(Workout).where(Workout.id == sample_workout.id)
            )
            workout = result.scalar_one_or_none()
            assert workout is not None
            assert str(workout.date) == new_date
            assert workout.duration_minutes == 60
            assert workout.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_edit_workout_replaces_exercises(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
        sample_exercises: list[Exercise],
        test_user: User,
    ):
        """Editing a workout should replace old exercises with new ones."""
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercises[0].id,
                    "sets": [{"weight": 300, "reps": 3}],
                },
                {
                    "exercise_id": sample_exercises[1].id,
                    "sets": [{"weight": 50, "reps": 15}],
                },
            ],
        )
        resp = await authenticated_client.post(
            f"/workouts/{sample_workout.id}/edit", data=form
        )
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            we_result = await session.execute(
                select(WorkoutExercise).where(
                    WorkoutExercise.workout_id == sample_workout.id
                )
            )
            workout_exercises = we_result.scalars().all()
            assert len(workout_exercises) == 2
            exercise_ids = {we.exercise_id for we in workout_exercises}
            assert sample_exercises[0].id in exercise_ids
            assert sample_exercises[1].id in exercise_ids

    @pytest.mark.asyncio
    async def test_edit_nonexistent_workout_redirects(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 100, "reps": 10}],
                }
            ],
        )
        resp = await authenticated_client.post("/workouts/99999/edit", data=form)
        assert resp.status_code == 303
        assert "/workouts/" in resp.headers["location"]


# ---------------------------------------------------------------------------
# Tests – Delete Workout
# ---------------------------------------------------------------------------


class TestDeleteWorkout:
    """Tests for POST /workouts/{workout_id}/delete."""

    @pytest.mark.asyncio
    async def test_delete_workout_redirects(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        resp = await authenticated_client.post(f"/workouts/{sample_workout.id}/delete")
        assert resp.status_code == 303
        assert "/workouts/" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_delete_workout_removes_from_db(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
        test_user: User,
    ):
        workout_id = sample_workout.id
        resp = await authenticated_client.post(f"/workouts/{workout_id}/delete")
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            result = await session.execute(
                select(Workout).where(Workout.id == workout_id)
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_workout_cascades_exercises_and_sets(
        self,
        authenticated_client: AsyncClient,
        sample_workout: Workout,
    ):
        workout_id = sample_workout.id

        # Confirm exercises/sets exist before delete
        async with test_async_session_maker() as session:
            we_result = await session.execute(
                select(func.count(WorkoutExercise.id)).where(
                    WorkoutExercise.workout_id == workout_id
                )
            )
            assert (we_result.scalar() or 0) > 0

        resp = await authenticated_client.post(f"/workouts/{workout_id}/delete")
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            we_result = await session.execute(
                select(func.count(WorkoutExercise.id)).where(
                    WorkoutExercise.workout_id == workout_id
                )
            )
            assert (we_result.scalar() or 0) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_workout_redirects(
        self,
        authenticated_client: AsyncClient,
    ):
        resp = await authenticated_client.post("/workouts/99999/delete")
        assert resp.status_code == 303


# ---------------------------------------------------------------------------
# Tests – PR Detection on Save
# ---------------------------------------------------------------------------


class TestPRDetection:
    """Tests for personal record detection when saving a workout."""

    @pytest.mark.asyncio
    async def test_pr_created_on_first_workout(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [
                        {"weight": 200, "reps": 5},
                        {"weight": 180, "reps": 8},
                    ],
                }
            ],
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            pr_result = await session.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == test_user.id,
                    PersonalRecord.exercise_id == sample_exercise.id,
                )
            )
            prs = pr_result.scalars().all()
            pr_types = {pr.type for pr in prs}
            # Should have weight, reps, and volume PRs
            assert "weight" in pr_types
            assert "reps" in pr_types
            assert "volume" in pr_types

            weight_pr = next(pr for pr in prs if pr.type == "weight")
            assert weight_pr.value == 200.0

            reps_pr = next(pr for pr in prs if pr.type == "reps")
            assert reps_pr.value == 8.0

    @pytest.mark.asyncio
    async def test_pr_updated_when_beaten(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        # First workout
        form1 = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 100, "reps": 10}],
                }
            ],
        )
        resp1 = await authenticated_client.post("/workouts/new", data=form1)
        assert resp1.status_code == 303

        # Second workout with higher weight
        form2 = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 150, "reps": 10}],
                }
            ],
        )
        resp2 = await authenticated_client.post("/workouts/new", data=form2)
        assert resp2.status_code == 303

        async with test_async_session_maker() as session:
            pr_result = await session.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == test_user.id,
                    PersonalRecord.exercise_id == sample_exercise.id,
                    PersonalRecord.type == "weight",
                )
            )
            weight_pr = pr_result.scalar_one_or_none()
            assert weight_pr is not None
            assert weight_pr.value == 150.0

    @pytest.mark.asyncio
    async def test_pr_not_updated_when_not_beaten(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        # First workout with high weight
        form1 = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 200, "reps": 5}],
                }
            ],
        )
        resp1 = await authenticated_client.post("/workouts/new", data=form1)
        assert resp1.status_code == 303

        # Second workout with lower weight
        form2 = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 150, "reps": 5}],
                }
            ],
        )
        resp2 = await authenticated_client.post("/workouts/new", data=form2)
        assert resp2.status_code == 303

        async with test_async_session_maker() as session:
            pr_result = await session.execute(
                select(PersonalRecord).where(
                    PersonalRecord.user_id == test_user.id,
                    PersonalRecord.exercise_id == sample_exercise.id,
                    PersonalRecord.type == "weight",
                )
            )
            weight_pr = pr_result.scalar_one_or_none()
            assert weight_pr is not None
            # PR should remain at 200, not downgraded to 150
            assert weight_pr.value == 200.0


# ---------------------------------------------------------------------------
# Tests – Save as Template
# ---------------------------------------------------------------------------


class TestSaveAsTemplate:
    """Tests for the save-as-template feature when creating a workout."""

    @pytest.mark.asyncio
    async def test_save_workout_as_template(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 135, "reps": 10}],
                }
            ],
            save_as_template=True,
            template_name="My Push Day",
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            tmpl_result = await session.execute(
                select(WorkoutTemplate).where(
                    WorkoutTemplate.user_id == test_user.id,
                    WorkoutTemplate.name == "My Push Day",
                )
            )
            template = tmpl_result.scalar_one_or_none()
            assert template is not None
            assert template.is_system is False

            te_result = await session.execute(
                select(TemplateExercise).where(
                    TemplateExercise.template_id == template.id
                )
            )
            template_exercises = te_result.scalars().all()
            assert len(template_exercises) == 1
            assert template_exercises[0].exercise_id == sample_exercise.id

    @pytest.mark.asyncio
    async def test_save_workout_without_template_flag(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        test_user: User,
    ):
        """When save_as_template is not checked, no template should be created."""
        form = _workout_form_data(
            workout_date=date.today().isoformat(),
            exercises=[
                {
                    "exercise_id": sample_exercise.id,
                    "sets": [{"weight": 135, "reps": 10}],
                }
            ],
            save_as_template=False,
        )
        resp = await authenticated_client.post("/workouts/new", data=form)
        assert resp.status_code == 303

        async with test_async_session_maker() as session:
            tmpl_result = await session.execute(
                select(func.count(WorkoutTemplate.id)).where(
                    WorkoutTemplate.user_id == test_user.id,
                    WorkoutTemplate.is_system == False,
                )
            )
            count = tmpl_result.scalar() or 0
            assert count == 0


# ---------------------------------------------------------------------------
# Tests – New Workout Form
# ---------------------------------------------------------------------------


class TestNewWorkoutForm:
    """Tests for GET /workouts/new."""

    @pytest.mark.asyncio
    async def test_new_workout_form_renders(
        self,
        authenticated_client: AsyncClient,
    ):
        resp = await authenticated_client.get("/workouts/new")
        assert resp.status_code == 200
        assert b"Log Workout" in resp.content

    @pytest.mark.asyncio
    async def test_new_workout_form_with_template(
        self,
        authenticated_client: AsyncClient,
        sample_template: WorkoutTemplate,
    ):
        resp = await authenticated_client.get(
            f"/workouts/new?template_id={sample_template.id}"
        )
        assert resp.status_code == 200
        assert b"Log Workout" in resp.content

    @pytest.mark.asyncio
    async def test_new_workout_form_with_date_param(
        self,
        authenticated_client: AsyncClient,
    ):
        target_date = "2024-06-15"
        resp = await authenticated_client.get(f"/workouts/new?date={target_date}")
        assert resp.status_code == 200
        assert target_date.encode() in resp.content

    @pytest.mark.asyncio
    async def test_new_workout_form_requires_auth(
        self,
        client: AsyncClient,
    ):
        resp = await client.get("/workouts/new")
        assert resp.status_code in (302, 303, 401)