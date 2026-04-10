import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.body_measurement import BodyMeasurement
from models.user import User
from tests.conftest import make_auth_cookie


@pytest.mark.asyncio
async def test_measurements_page_requires_auth(client: AsyncClient):
    """Unauthenticated users should be redirected from measurements page."""
    response = await client.get("/measurements/")
    assert response.status_code in (302, 401, 403)


@pytest.mark.asyncio
async def test_measurements_page_loads_for_authenticated_user(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Authenticated users can access the measurements list page."""
    response = await authenticated_client.get("/measurements/")
    assert response.status_code == 200
    assert b"Body Measurements" in response.content


@pytest.mark.asyncio
async def test_new_measurement_form_loads(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """The new measurement form page should load successfully."""
    response = await authenticated_client.get("/measurements/new")
    assert response.status_code == 200
    assert b"Log Measurement" in response.content


@pytest.mark.asyncio
async def test_create_measurement_success(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Creating a measurement with valid data should redirect to the list."""
    today = date.today().isoformat()
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": today,
            "weight": "180.5",
            "body_fat_percent": "15.0",
            "chest": "42.0",
            "waist": "33.0",
            "hips": "",
            "arms": "15.5",
            "thighs": "24.0",
        },
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_create_measurement_weight_only(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Creating a measurement with only weight should succeed."""
    measurement_date = (date.today() - timedelta(days=5)).isoformat()
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": measurement_date,
            "weight": "175.0",
            "body_fat_percent": "",
            "chest": "",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_create_measurement_no_values_fails(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Creating a measurement with no values should return a 422 error."""
    measurement_date = (date.today() - timedelta(days=10)).isoformat()
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": measurement_date,
            "weight": "",
            "body_fat_percent": "",
            "chest": "",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 422
    assert b"at least one measurement" in response.content.lower()


@pytest.mark.asyncio
async def test_create_measurement_invalid_date_fails(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Creating a measurement with an invalid date should return a 422 error."""
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": "not-a-date",
            "weight": "180.0",
            "body_fat_percent": "",
            "chest": "",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 422
    assert b"Invalid date" in response.content


@pytest.mark.asyncio
async def test_create_measurement_unique_per_user_date(
    authenticated_client: AsyncClient,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """Creating a measurement for a date that already has one should return a 409 conflict."""
    existing_date = sample_measurement.measurement_date.isoformat()
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": existing_date,
            "weight": "190.0",
            "body_fat_percent": "",
            "chest": "",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 409
    assert b"already exists" in response.content.lower()


@pytest.mark.asyncio
async def test_measurement_history_shows_entries(
    authenticated_client: AsyncClient,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """The measurements list page should display existing measurements."""
    response = await authenticated_client.get("/measurements/")
    assert response.status_code == 200
    assert b"175.5" in response.content


@pytest.mark.asyncio
async def test_measurement_history_pagination(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Measurement history should support pagination."""
    base_date = date.today() - timedelta(days=100)
    for i in range(25):
        measurement = BodyMeasurement(
            user_id=test_user.id,
            measurement_date=base_date + timedelta(days=i),
            weight=170.0 + i * 0.1,
        )
        db_session.add(measurement)
    await db_session.flush()

    response_page1 = await authenticated_client.get("/measurements/?page=1&page_size=10")
    assert response_page1.status_code == 200

    response_page2 = await authenticated_client.get("/measurements/?page=2&page_size=10")
    assert response_page2.status_code == 200

    response_page3 = await authenticated_client.get("/measurements/?page=3&page_size=10")
    assert response_page3.status_code == 200


@pytest.mark.asyncio
async def test_edit_measurement_form_loads(
    authenticated_client: AsyncClient,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """The edit measurement form should load for an existing measurement."""
    response = await authenticated_client.get(
        f"/measurements/{sample_measurement.id}/edit"
    )
    assert response.status_code == 200
    assert b"Edit Measurement" in response.content


@pytest.mark.asyncio
async def test_edit_measurement_success(
    authenticated_client: AsyncClient,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """Editing a measurement with valid data should redirect to the list."""
    response = await authenticated_client.post(
        f"/measurements/{sample_measurement.id}/edit",
        data={
            "measurement_date": sample_measurement.measurement_date.isoformat(),
            "weight": "182.0",
            "body_fat_percent": "16.5",
            "chest": "43.0",
            "waist": "32.5",
            "hips": "",
            "arms": "16.0",
            "thighs": "25.0",
        },
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_edit_measurement_change_date_conflict(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """Editing a measurement to a date that already has one should return a 409 conflict."""
    date1 = date.today() - timedelta(days=20)
    date2 = date.today() - timedelta(days=21)

    m1 = BodyMeasurement(
        user_id=test_user.id,
        measurement_date=date1,
        weight=170.0,
    )
    m2 = BodyMeasurement(
        user_id=test_user.id,
        measurement_date=date2,
        weight=171.0,
    )
    db_session.add(m1)
    db_session.add(m2)
    await db_session.flush()
    await db_session.refresh(m1)
    await db_session.refresh(m2)

    response = await authenticated_client.post(
        f"/measurements/{m2.id}/edit",
        data={
            "measurement_date": date1.isoformat(),
            "weight": "172.0",
            "body_fat_percent": "",
            "chest": "",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 409
    assert b"already exists" in response.content.lower()


@pytest.mark.asyncio
async def test_edit_nonexistent_measurement_redirects(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Editing a measurement that doesn't exist should redirect to the list."""
    response = await authenticated_client.get("/measurements/99999/edit")
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_delete_measurement_success(
    authenticated_client: AsyncClient,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """Deleting a measurement should redirect to the list."""
    response = await authenticated_client.post(
        f"/measurements/{sample_measurement.id}/delete"
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_delete_nonexistent_measurement_redirects(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Deleting a measurement that doesn't exist should redirect to the list."""
    response = await authenticated_client.post("/measurements/99999/delete")
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_measurement_trend_summary_displayed(
    authenticated_client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
):
    """The measurements list page should display trend summary data."""
    old_date = date.today() - timedelta(days=45)
    recent_date = date.today() - timedelta(days=1)

    m_old = BodyMeasurement(
        user_id=test_user.id,
        measurement_date=old_date,
        weight=185.0,
        body_fat_percent=20.0,
        waist=36.0,
    )
    m_recent = BodyMeasurement(
        user_id=test_user.id,
        measurement_date=recent_date,
        weight=180.0,
        body_fat_percent=18.0,
        waist=34.0,
    )
    db_session.add(m_old)
    db_session.add(m_recent)
    await db_session.flush()

    response = await authenticated_client.get("/measurements/")
    assert response.status_code == 200
    assert b"Current Weight" in response.content
    assert b"180.0" in response.content


@pytest.mark.asyncio
async def test_measurement_not_accessible_by_other_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    sample_measurement: BodyMeasurement,
):
    """A user should not be able to edit another user's measurement."""
    other_user = User(
        display_name="Other User",
        email="other@example.com",
        username="otheruser",
        password_hash="$2b$12$dummyhashvalue1234567890abcdefghijklmnopqrstuvwxyz",
        role="user",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()
    await db_session.refresh(other_user)

    other_cookies = make_auth_cookie(other_user)
    client.cookies.update(other_cookies)

    response = await client.get(f"/measurements/{sample_measurement.id}/edit")
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_create_measurement_negative_weight_ignored(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """Negative weight values should be treated as empty (ignored)."""
    measurement_date = (date.today() - timedelta(days=15)).isoformat()
    response = await authenticated_client.post(
        "/measurements/new",
        data={
            "measurement_date": measurement_date,
            "weight": "-5.0",
            "body_fat_percent": "",
            "chest": "40.0",
            "waist": "",
            "hips": "",
            "arms": "",
            "thighs": "",
        },
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/measurements/"


@pytest.mark.asyncio
async def test_measurements_empty_state(
    authenticated_client: AsyncClient,
    test_user: User,
):
    """The measurements page should show an empty state when no measurements exist."""
    response = await authenticated_client.get("/measurements/")
    assert response.status_code == 200
    assert b"No measurements yet" in response.content or b"Add Your First Measurement" in response.content