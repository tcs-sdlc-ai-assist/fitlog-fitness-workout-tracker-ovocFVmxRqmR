import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.body_measurement import BodyMeasurement


async def log_measurement(
    db: AsyncSession,
    user_id: int,
    measurement_date: date,
    weight: Optional[float] = None,
    body_fat_percent: Optional[float] = None,
    chest: Optional[float] = None,
    waist: Optional[float] = None,
    hips: Optional[float] = None,
    arms: Optional[float] = None,
    thighs: Optional[float] = None,
    notes: Optional[str] = None,
) -> BodyMeasurement:
    """Log a new body measurement. Enforces unique per user/date."""
    existing_stmt = select(BodyMeasurement).where(
        and_(
            BodyMeasurement.user_id == user_id,
            BodyMeasurement.measurement_date == measurement_date,
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalars().first()

    if existing is not None:
        raise ValueError(
            f"A measurement already exists for {measurement_date}. "
            "Please edit the existing entry instead."
        )

    measurement = BodyMeasurement(
        user_id=user_id,
        measurement_date=measurement_date,
        weight=weight,
        body_fat_percent=body_fat_percent,
        chest=chest,
        waist=waist,
        hips=hips,
        arms=arms,
        thighs=thighs,
        notes=notes,
    )
    db.add(measurement)
    await db.flush()
    await db.refresh(measurement)
    return measurement


async def get_measurement_history(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Get paginated measurement history sorted by date descending."""
    count_stmt = select(func.count(BodyMeasurement.id)).where(
        BodyMeasurement.user_id == user_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    total_pages = max(1, (total + page_size - 1) // page_size)

    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(desc(BodyMeasurement.measurement_date))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    measurements = list(result.scalars().all())

    return {
        "measurements": measurements,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_measurement_by_id(
    db: AsyncSession,
    measurement_id: int,
    user_id: int,
) -> Optional[BodyMeasurement]:
    """Get a single measurement by ID, scoped to user."""
    stmt = select(BodyMeasurement).where(
        and_(
            BodyMeasurement.id == measurement_id,
            BodyMeasurement.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def edit_measurement(
    db: AsyncSession,
    measurement_id: int,
    user_id: int,
    measurement_date: Optional[date] = None,
    weight: Optional[float] = ...,
    body_fat_percent: Optional[float] = ...,
    chest: Optional[float] = ...,
    waist: Optional[float] = ...,
    hips: Optional[float] = ...,
    arms: Optional[float] = ...,
    thighs: Optional[float] = ...,
    notes: Optional[str] = ...,
) -> Optional[BodyMeasurement]:
    """Edit an existing measurement. Returns None if not found."""
    measurement = await get_measurement_by_id(db, measurement_id, user_id)
    if measurement is None:
        return None

    if measurement_date is not None and measurement_date != measurement.measurement_date:
        existing_stmt = select(BodyMeasurement).where(
            and_(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.measurement_date == measurement_date,
                BodyMeasurement.id != measurement_id,
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalars().first()
        if existing is not None:
            raise ValueError(
                f"A measurement already exists for {measurement_date}."
            )
        measurement.measurement_date = measurement_date

    if weight is not ...:
        measurement.weight = weight
    if body_fat_percent is not ...:
        measurement.body_fat_percent = body_fat_percent
    if chest is not ...:
        measurement.chest = chest
    if waist is not ...:
        measurement.waist = waist
    if hips is not ...:
        measurement.hips = hips
    if arms is not ...:
        measurement.arms = arms
    if thighs is not ...:
        measurement.thighs = thighs
    if notes is not ...:
        measurement.notes = notes

    await db.flush()
    await db.refresh(measurement)
    return measurement


async def delete_measurement(
    db: AsyncSession,
    measurement_id: int,
    user_id: int,
) -> bool:
    """Delete a measurement. Returns True if deleted, False if not found."""
    measurement = await get_measurement_by_id(db, measurement_id, user_id)
    if measurement is None:
        return False

    await db.delete(measurement)
    await db.flush()
    return True


async def _get_latest_measurement_before(
    db: AsyncSession,
    user_id: int,
    before_date: date,
) -> Optional[BodyMeasurement]:
    """Get the most recent measurement on or before a given date."""
    stmt = (
        select(BodyMeasurement)
        .where(
            and_(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.measurement_date <= before_date,
            )
        )
        .order_by(desc(BodyMeasurement.measurement_date))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_trend_summary(
    db: AsyncSession,
    user_id: int,
    days: int = 30,
) -> dict:
    """
    Get trend summaries for weight, body_fat, and waist.
    Compares the most recent measurement to the measurement closest to `days` ago.
    Returns a dict with keys: weight_trend, body_fat_trend, waist_trend.
    Each trend has: current_value, previous_value, change, change_percent.
    """
    today = date.today()
    past_date = today - timedelta(days=days)

    current_measurement = await _get_latest_measurement_before(db, user_id, today)
    previous_measurement = await _get_latest_measurement_before(db, user_id, past_date)

    def build_trend(metric: str, current_m: Optional[BodyMeasurement], previous_m: Optional[BodyMeasurement]) -> dict:
        current_value = None
        previous_value = None
        change = None
        change_percent = None

        if current_m is not None:
            current_value = getattr(current_m, metric, None)
        if previous_m is not None:
            previous_value = getattr(previous_m, metric, None)

        if current_value is not None and previous_value is not None:
            change = round(current_value - previous_value, 2)
            if previous_value != 0:
                change_percent = round((change / previous_value) * 100, 2)

        return {
            "metric": metric,
            "current_value": current_value,
            "previous_value": previous_value,
            "change": change,
            "change_percent": change_percent,
        }

    weight_trend = build_trend("weight", current_measurement, previous_measurement)
    body_fat_trend = build_trend("body_fat_percent", current_measurement, previous_measurement)
    waist_trend = build_trend("waist", current_measurement, previous_measurement)

    return {
        "weight_trend": weight_trend,
        "body_fat_trend": body_fat_trend,
        "waist_trend": waist_trend,
    }


async def get_current_weight(
    db: AsyncSession,
    user_id: int,
) -> Optional[float]:
    """Get the most recent weight measurement for a user."""
    stmt = (
        select(BodyMeasurement.weight)
        .where(
            and_(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.weight.isnot(None),
            )
        )
        .order_by(desc(BodyMeasurement.measurement_date))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar()


async def get_all_measurements_for_user(
    db: AsyncSession,
    user_id: int,
) -> list:
    """Get all measurements for a user, sorted by date ascending (for charts)."""
    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(BodyMeasurement.measurement_date)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())