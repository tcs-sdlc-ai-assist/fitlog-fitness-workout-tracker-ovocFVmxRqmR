import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from models.exercise import Exercise


async def create_template(
    db: AsyncSession,
    user_id: int,
    name: str,
    is_system: bool,
    exercises: list[dict],
) -> WorkoutTemplate:
    template = WorkoutTemplate(
        user_id=user_id,
        name=name.strip(),
        is_system=is_system,
    )
    db.add(template)
    await db.flush()

    for idx, ex_data in enumerate(exercises):
        exercise_id = ex_data.get("exercise_id")
        order_index = ex_data.get("order_index", idx)
        template_exercise = TemplateExercise(
            template_id=template.id,
            exercise_id=exercise_id,
            order_index=order_index,
        )
        db.add(template_exercise)

    await db.flush()

    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template.id)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
    )
    template = result.scalars().first()
    return template


async def clone_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
) -> Optional[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template_id)
        .options(selectinload(WorkoutTemplate.template_exercises))
    )
    source_template = result.scalars().first()
    if source_template is None:
        return None

    new_template = WorkoutTemplate(
        user_id=user_id,
        name=f"{source_template.name} (Copy)",
        is_system=False,
    )
    db.add(new_template)
    await db.flush()

    for te in source_template.template_exercises:
        new_te = TemplateExercise(
            template_id=new_template.id,
            exercise_id=te.exercise_id,
            order_index=te.order_index,
            sets_count=te.sets_count,
            default_reps=te.default_reps,
            default_weight=te.default_weight,
        )
        db.add(new_te)

    await db.flush()

    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == new_template.id)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
    )
    new_template = result.scalars().first()
    return new_template


async def edit_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
    name: Optional[str] = None,
    is_system: Optional[bool] = None,
    exercises: Optional[list[dict]] = None,
) -> Optional[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template_id)
        .options(selectinload(WorkoutTemplate.template_exercises))
    )
    template = result.scalars().first()
    if template is None:
        return None

    if template.user_id != user_id:
        return None

    if name is not None:
        template.name = name.strip()

    if is_system is not None:
        template.is_system = is_system

    if exercises is not None:
        for existing_te in template.template_exercises:
            await db.delete(existing_te)
        await db.flush()

        for idx, ex_data in enumerate(exercises):
            exercise_id = ex_data.get("exercise_id")
            order_index = ex_data.get("order_index", idx)
            new_te = TemplateExercise(
                template_id=template.id,
                exercise_id=exercise_id,
                order_index=order_index,
            )
            db.add(new_te)

    await db.flush()

    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template.id)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
    )
    template = result.scalars().first()
    return template


async def delete_template(
    db: AsyncSession,
    template_id: int,
    user_id: int,
) -> bool:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template_id)
    )
    template = result.scalars().first()
    if template is None:
        return False

    if template.user_id != user_id:
        return False

    await db.delete(template)
    await db.flush()
    return True


async def get_user_templates(
    db: AsyncSession,
    user_id: int,
) -> list[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == user_id, WorkoutTemplate.is_system == False)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
        .order_by(WorkoutTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return list(templates)


async def get_system_templates(
    db: AsyncSession,
) -> list[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.is_system == True)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
        .order_by(WorkoutTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return list(templates)


async def get_template_detail(
    db: AsyncSession,
    template_id: int,
) -> Optional[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template_id)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
    )
    template = result.scalars().first()
    return template


async def get_all_templates_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[WorkoutTemplate]:
    result = await db.execute(
        select(WorkoutTemplate)
        .where(
            (WorkoutTemplate.user_id == user_id) | (WorkoutTemplate.is_system == True)
        )
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
        .order_by(WorkoutTemplate.is_system.desc(), WorkoutTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return list(templates)


async def create_template_from_workout_exercises(
    db: AsyncSession,
    user_id: int,
    template_name: str,
    workout_exercises: list[dict],
) -> WorkoutTemplate:
    template = WorkoutTemplate(
        user_id=user_id,
        name=template_name.strip(),
        is_system=False,
    )
    db.add(template)
    await db.flush()

    for idx, we_data in enumerate(workout_exercises):
        exercise_id = we_data.get("exercise_id")
        order_index = we_data.get("order_index", idx)
        te = TemplateExercise(
            template_id=template.id,
            exercise_id=exercise_id,
            order_index=order_index,
        )
        db.add(te)

    await db.flush()

    result = await db.execute(
        select(WorkoutTemplate)
        .where(WorkoutTemplate.id == template.id)
        .options(selectinload(WorkoutTemplate.template_exercises).selectinload(TemplateExercise.exercise))
    )
    template = result.scalars().first()
    return template


def enrich_template_exercises(template: WorkoutTemplate) -> list[dict]:
    enriched = []
    if template.template_exercises:
        for te in sorted(template.template_exercises, key=lambda x: x.order_index):
            exercise_name = None
            muscle_group = None
            equipment = None
            if te.exercise:
                exercise_name = te.exercise.name
                muscle_group = te.exercise.muscle_group
                equipment = te.exercise.equipment
            enriched.append({
                "id": te.id,
                "template_id": te.template_id,
                "exercise_id": te.exercise_id,
                "order_index": te.order_index,
                "exercise_name": exercise_name,
                "muscle_group": muscle_group,
                "equipment": equipment,
                "sets_count": te.sets_count,
                "default_reps": te.default_reps,
                "default_weight": te.default_weight,
            })
    return enriched