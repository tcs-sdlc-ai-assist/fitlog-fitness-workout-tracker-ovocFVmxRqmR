import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.exercise import Exercise
from models.user import User
from tests.conftest import make_auth_cookie


@pytest.mark.asyncio
class TestExerciseLibrary:
    """Tests for the public exercise library page."""

    async def test_exercise_library_accessible_without_auth(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library page should be accessible without authentication."""
        response = await client.get("/exercises/")
        assert response.status_code == 200
        assert b"Exercise Library" in response.content

    async def test_exercise_library_lists_exercises(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library should display existing exercises."""
        response = await client.get("/exercises/")
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_exercise_library_search_by_name(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library should filter exercises by search query."""
        response = await client.get("/exercises/", params={"q": "Test Bench"})
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_exercise_library_search_no_results(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library should show no results for non-matching search."""
        response = await client.get("/exercises/", params={"q": "NonExistentExercise12345"})
        assert response.status_code == 200
        assert sample_exercise.name.encode() not in response.content

    async def test_exercise_library_filter_by_muscle_group(
        self, client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Exercise library should filter exercises by muscle group."""
        response = await client.get("/exercises/", params={"muscle_group": "Chest"})
        assert response.status_code == 200
        assert b"Test Bench Press" in response.content
        assert b"Test Squat" not in response.content

    async def test_exercise_library_filter_by_equipment(
        self, client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Exercise library should filter exercises by equipment type."""
        response = await client.get("/exercises/", params={"equipment": "Bodyweight"})
        assert response.status_code == 200
        assert b"Test Pull-Up" in response.content
        assert b"Test Bench Press" not in response.content

    async def test_exercise_library_combined_filters(
        self, client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Exercise library should support combined search and filter."""
        response = await client.get(
            "/exercises/",
            params={"q": "Test", "muscle_group": "Legs", "equipment": "Barbell"},
        )
        assert response.status_code == 200
        assert b"Test Squat" in response.content
        assert b"Test Bench Press" not in response.content
        assert b"Test Pull-Up" not in response.content

    async def test_exercise_library_pagination_defaults(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library should handle default pagination."""
        response = await client.get("/exercises/", params={"page": 1, "page_size": 20})
        assert response.status_code == 200

    async def test_exercise_library_invalid_page_number(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise library should handle invalid page numbers gracefully."""
        response = await client.get("/exercises/", params={"page": -1})
        assert response.status_code == 200


@pytest.mark.asyncio
class TestExerciseDetail:
    """Tests for the exercise detail page."""

    async def test_exercise_detail_accessible_without_auth(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise detail page should be accessible without authentication."""
        response = await client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_exercise_detail_shows_metadata(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise detail page should display exercise metadata."""
        response = await client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert sample_exercise.muscle_group.encode() in response.content
        assert sample_exercise.equipment.encode() in response.content

    async def test_exercise_detail_shows_instructions(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Exercise detail page should display instructions if available."""
        response = await client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert sample_exercise.instructions.encode() in response.content

    async def test_exercise_detail_not_found(
        self, client: AsyncClient
    ):
        """Exercise detail page should return 404 for non-existent exercise."""
        response = await client.get("/exercises/99999")
        assert response.status_code == 404

    async def test_exercise_detail_shows_history_for_authenticated_user(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
        sample_workout,
    ):
        """Exercise detail page should show workout history for authenticated users."""
        response = await authenticated_client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert b"Recent History" in response.content

    async def test_exercise_detail_shows_prs_section_for_authenticated_user(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        """Exercise detail page should show personal records section for authenticated users."""
        response = await authenticated_client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert b"Personal Records" in response.content

    async def test_exercise_detail_admin_sees_edit_button(
        self,
        admin_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        """Admin should see edit and delete buttons on exercise detail page."""
        response = await admin_client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        assert b"Edit" in response.content
        assert b"Delete" in response.content

    async def test_exercise_detail_regular_user_no_edit_button(
        self,
        authenticated_client: AsyncClient,
        sample_exercise: Exercise,
    ):
        """Regular user should not see edit/delete buttons on exercise detail page."""
        response = await authenticated_client.get(f"/exercises/{sample_exercise.id}")
        assert response.status_code == 200
        content = response.content.decode()
        assert f'/exercises/{sample_exercise.id}/edit' not in content


@pytest.mark.asyncio
class TestAdminExerciseCreate:
    """Tests for admin exercise creation."""

    async def test_admin_can_access_new_exercise_form(
        self, admin_client: AsyncClient
    ):
        """Admin should be able to access the new exercise form."""
        response = await admin_client.get("/admin/exercises/new")
        assert response.status_code == 200
        assert b"Add" in response.content or b"Exercise" in response.content

    async def test_admin_can_create_exercise(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin should be able to create a new exercise."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": "New Test Exercise",
                "muscle_group": "Back",
                "equipment": "Cable",
                "instructions": "Pull the cable toward you.",
                "is_system": "true",
            },
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/admin/dashboard/"

        result = await db_session.execute(
            select(Exercise).where(Exercise.name == "New Test Exercise")
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.muscle_group == "Back"
        assert exercise.equipment == "Cable"
        assert exercise.is_system is True

    async def test_admin_create_exercise_missing_name(
        self, admin_client: AsyncClient
    ):
        """Admin should get an error when creating exercise without name."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": "",
                "muscle_group": "Back",
                "equipment": "Cable",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code == 400

    async def test_admin_create_exercise_missing_muscle_group(
        self, admin_client: AsyncClient
    ):
        """Admin should get an error when creating exercise without muscle group."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": "Some Exercise",
                "muscle_group": "",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code == 400

    async def test_admin_create_exercise_missing_equipment(
        self, admin_client: AsyncClient
    ):
        """Admin should get an error when creating exercise without equipment."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": "Some Exercise",
                "muscle_group": "Chest",
                "equipment": "",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code == 400

    async def test_admin_create_exercise_duplicate_name(
        self, admin_client: AsyncClient, sample_exercise: Exercise
    ):
        """Admin should get an error when creating exercise with duplicate name."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": sample_exercise.name,
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code == 400
        assert b"already exists" in response.content

    async def test_admin_create_exercise_not_system(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin should be able to create a non-system exercise."""
        response = await admin_client.post(
            "/admin/exercises/create",
            data={
                "name": "Custom Admin Exercise",
                "muscle_group": "Arms",
                "equipment": "Dumbbell",
                "instructions": "Curl the dumbbell.",
                "is_system": "",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(Exercise).where(Exercise.name == "Custom Admin Exercise")
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.is_system is False


@pytest.mark.asyncio
class TestAdminExerciseEdit:
    """Tests for admin exercise editing."""

    async def test_admin_can_access_edit_exercise_form(
        self, admin_client: AsyncClient, sample_exercise: Exercise
    ):
        """Admin should be able to access the edit exercise form."""
        response = await admin_client.get(f"/admin/exercises/{sample_exercise.id}/edit")
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_admin_can_edit_exercise(
        self, admin_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Admin should be able to update an exercise."""
        response = await admin_client.post(
            f"/admin/exercises/{sample_exercise.id}/edit",
            data={
                "name": "Updated Bench Press",
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "Updated instructions.",
                "is_system": "true",
            },
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/admin/dashboard/"

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == sample_exercise.id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.name == "Updated Bench Press"
        assert exercise.instructions == "Updated instructions."

    async def test_admin_edit_exercise_duplicate_name(
        self, admin_client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Admin should get an error when editing exercise to a duplicate name."""
        other_exercise = sample_exercises[0]
        response = await admin_client.post(
            f"/admin/exercises/{sample_exercise.id}/edit",
            data={
                "name": other_exercise.name,
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "true",
            },
        )
        assert response.status_code == 400
        assert b"already exists" in response.content

    async def test_admin_edit_exercise_missing_fields(
        self, admin_client: AsyncClient, sample_exercise: Exercise
    ):
        """Admin should get an error when editing exercise with missing required fields."""
        response = await admin_client.post(
            f"/admin/exercises/{sample_exercise.id}/edit",
            data={
                "name": "",
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code == 400

    async def test_admin_edit_nonexistent_exercise_redirects(
        self, admin_client: AsyncClient
    ):
        """Admin should be redirected when trying to edit a non-existent exercise."""
        response = await admin_client.get("/admin/exercises/99999/edit")
        assert response.status_code == 302
        assert response.headers.get("location") == "/admin/dashboard/"

    async def test_admin_edit_exercise_can_change_muscle_group(
        self, admin_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Admin should be able to change the muscle group of an exercise."""
        response = await admin_client.post(
            f"/admin/exercises/{sample_exercise.id}/edit",
            data={
                "name": sample_exercise.name,
                "muscle_group": "Shoulders",
                "equipment": sample_exercise.equipment,
                "instructions": sample_exercise.instructions or "",
                "is_system": "true",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == sample_exercise.id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.muscle_group == "Shoulders"


@pytest.mark.asyncio
class TestAdminExerciseDelete:
    """Tests for admin exercise deletion."""

    async def test_admin_can_delete_exercise(
        self, admin_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Admin should be able to delete an exercise."""
        exercise_id = sample_exercise.id
        response = await admin_client.post(f"/admin/exercises/{exercise_id}/delete")
        assert response.status_code == 303
        assert response.headers.get("location") == "/admin/dashboard/"

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is None

    async def test_admin_delete_nonexistent_exercise_redirects(
        self, admin_client: AsyncClient
    ):
        """Admin should be redirected when trying to delete a non-existent exercise."""
        response = await admin_client.post("/admin/exercises/99999/delete")
        assert response.status_code == 303
        assert response.headers.get("location") == "/admin/dashboard/"


@pytest.mark.asyncio
class TestNonAdminCannotManageExercises:
    """Tests ensuring non-admin users cannot create, edit, or delete exercises."""

    async def test_regular_user_cannot_access_admin_new_exercise(
        self, authenticated_client: AsyncClient
    ):
        """Regular user should not be able to access admin new exercise form."""
        response = await authenticated_client.get("/admin/exercises/new")
        assert response.status_code in (403, 302, 307)

    async def test_regular_user_cannot_create_exercise_via_admin(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Regular user should not be able to create exercises via admin route."""
        response = await authenticated_client.post(
            "/admin/exercises/create",
            data={
                "name": "Unauthorized Exercise",
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code in (403, 302, 307)

        result = await db_session.execute(
            select(Exercise).where(Exercise.name == "Unauthorized Exercise")
        )
        exercise = result.scalar_one_or_none()
        assert exercise is None

    async def test_regular_user_cannot_edit_exercise_via_admin(
        self, authenticated_client: AsyncClient, sample_exercise: Exercise
    ):
        """Regular user should not be able to edit exercises via admin route."""
        response = await authenticated_client.post(
            f"/admin/exercises/{sample_exercise.id}/edit",
            data={
                "name": "Hacked Exercise Name",
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code in (403, 302, 307)

    async def test_regular_user_cannot_delete_exercise_via_admin(
        self, authenticated_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Regular user should not be able to delete exercises via admin route."""
        exercise_id = sample_exercise.id
        response = await authenticated_client.post(f"/admin/exercises/{exercise_id}/delete")
        assert response.status_code in (403, 302, 307)

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None

    async def test_regular_user_redirected_from_exercises_new_form(
        self, authenticated_client: AsyncClient
    ):
        """Regular user accessing /exercises/new should be redirected to exercise library."""
        response = await authenticated_client.get("/exercises/new")
        assert response.status_code == 303
        assert response.headers.get("location") == "/exercises/"

    async def test_regular_user_redirected_from_exercises_edit_form(
        self, authenticated_client: AsyncClient, sample_exercise: Exercise
    ):
        """Regular user accessing exercise edit form should be redirected."""
        response = await authenticated_client.get(f"/exercises/{sample_exercise.id}/edit")
        assert response.status_code == 303
        assert response.headers.get("location") == f"/exercises/{sample_exercise.id}"

    async def test_regular_user_cannot_delete_exercise_via_exercises_route(
        self, authenticated_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Regular user should not be able to delete exercises via /exercises/ route."""
        exercise_id = sample_exercise.id
        response = await authenticated_client.post(f"/exercises/{exercise_id}/delete")
        assert response.status_code == 303
        assert response.headers.get("location") == f"/exercises/{exercise_id}"

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None

    async def test_unauthenticated_user_cannot_access_admin_exercises(
        self, client: AsyncClient
    ):
        """Unauthenticated user should not be able to access admin exercise routes."""
        response = await client.get("/admin/exercises/new")
        assert response.status_code in (401, 302, 307)

    async def test_unauthenticated_user_cannot_create_exercise(
        self, client: AsyncClient
    ):
        """Unauthenticated user should not be able to create exercises."""
        response = await client.post(
            "/admin/exercises/create",
            data={
                "name": "Anon Exercise",
                "muscle_group": "Chest",
                "equipment": "Barbell",
                "instructions": "",
                "is_system": "",
            },
        )
        assert response.status_code in (401, 302, 307)


@pytest.mark.asyncio
class TestExerciseSearchService:
    """Tests for exercise search and filter service layer via HTTP."""

    async def test_search_exercises_returns_all_when_no_filters(
        self, client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Search should return all exercises when no filters are applied."""
        response = await client.get("/exercises/")
        assert response.status_code == 200
        content = response.content.decode()
        assert sample_exercise.name in content
        for ex in sample_exercises:
            assert ex.name in content

    async def test_search_exercises_case_insensitive(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Search should be case-insensitive."""
        response = await client.get("/exercises/", params={"q": "test bench press"})
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_search_exercises_partial_match(
        self, client: AsyncClient, sample_exercise: Exercise
    ):
        """Search should support partial name matching."""
        response = await client.get("/exercises/", params={"q": "Bench"})
        assert response.status_code == 200
        assert sample_exercise.name.encode() in response.content

    async def test_filter_exercises_multiple_muscle_groups_exist(
        self, client: AsyncClient, sample_exercise: Exercise, sample_exercises: list[Exercise]
    ):
        """Filtering by one muscle group should exclude exercises from other groups."""
        response = await client.get("/exercises/", params={"muscle_group": "Back"})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Pull-Up" in content
        assert "Test Bench Press" not in content
        assert "Test Squat" not in content


@pytest.mark.asyncio
class TestAdminExerciseFormViaExercisesRoute:
    """Tests for exercise management via /exercises/ routes (admin only)."""

    async def test_admin_can_access_exercises_new_form(
        self, admin_client: AsyncClient
    ):
        """Admin should be able to access /exercises/new form."""
        response = await admin_client.get("/exercises/new")
        assert response.status_code == 200

    async def test_admin_can_create_exercise_via_exercises_route(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        """Admin should be able to create exercise via /exercises/new POST."""
        response = await admin_client.post(
            "/exercises/new",
            data={
                "name": "Route Created Exercise",
                "muscle_group": "Core",
                "equipment": "Bodyweight",
                "instructions": "Hold a plank position.",
                "is_system": "true",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(Exercise).where(Exercise.name == "Route Created Exercise")
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.muscle_group == "Core"

    async def test_admin_can_edit_exercise_via_exercises_route(
        self, admin_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Admin should be able to edit exercise via /exercises/{id}/edit POST."""
        response = await admin_client.post(
            f"/exercises/{sample_exercise.id}/edit",
            data={
                "name": "Route Updated Exercise",
                "muscle_group": "Legs",
                "equipment": "Machine",
                "instructions": "Updated via route.",
                "is_system": "true",
            },
        )
        assert response.status_code == 303

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == sample_exercise.id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is not None
        assert exercise.name == "Route Updated Exercise"
        assert exercise.muscle_group == "Legs"

    async def test_admin_can_delete_exercise_via_exercises_route(
        self, admin_client: AsyncClient, sample_exercise: Exercise, db_session: AsyncSession
    ):
        """Admin should be able to delete exercise via /exercises/{id}/delete POST."""
        exercise_id = sample_exercise.id
        response = await admin_client.post(f"/exercises/{exercise_id}/delete")
        assert response.status_code == 303
        assert response.headers.get("location") == "/exercises/"

        result = await db_session.execute(
            select(Exercise).where(Exercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()
        assert exercise is None