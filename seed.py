import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
from sqlalchemy import select, func

from database import async_session_maker, create_tables
from models.user import User
from models.exercise import Exercise
from models.workout_template import WorkoutTemplate
from models.template_exercise import TemplateExercise
from utils.security import hash_password


ADMIN_USER = {
    "display_name": "Admin",
    "email": "admin@fitlog.com",
    "username": "admin",
    "password": "admin123",
    "role": "admin",
}

EXERCISES = [
    # Chest
    {"name": "Barbell Bench Press", "muscle_group": "Chest", "equipment": "Barbell", "instructions": "Lie on a flat bench, grip the barbell slightly wider than shoulder-width. Lower the bar to your chest, then press it back up to full arm extension.", "is_system": True},
    {"name": "Incline Dumbbell Press", "muscle_group": "Chest", "equipment": "Dumbbell", "instructions": "Set an adjustable bench to a 30-45 degree incline. Press dumbbells from chest level to full extension above your upper chest.", "is_system": True},
    {"name": "Dumbbell Flyes", "muscle_group": "Chest", "equipment": "Dumbbell", "instructions": "Lie on a flat bench with dumbbells extended above your chest. Lower the weights in a wide arc until you feel a stretch, then bring them back together.", "is_system": True},
    {"name": "Cable Crossover", "muscle_group": "Chest", "equipment": "Cable", "instructions": "Stand between two cable stations with handles set high. Pull the handles down and together in front of your chest in a hugging motion.", "is_system": True},
    {"name": "Push-Up", "muscle_group": "Chest", "equipment": "Bodyweight", "instructions": "Start in a plank position with hands slightly wider than shoulder-width. Lower your body until your chest nearly touches the floor, then push back up.", "is_system": True},
    {"name": "Decline Bench Press", "muscle_group": "Chest", "equipment": "Barbell", "instructions": "Lie on a decline bench, grip the barbell at shoulder width. Lower the bar to your lower chest, then press it back up.", "is_system": True},

    # Back
    {"name": "Barbell Deadlift", "muscle_group": "Back", "equipment": "Barbell", "instructions": "Stand with feet hip-width apart, grip the barbell. Keep your back straight and lift the bar by extending your hips and knees.", "is_system": True},
    {"name": "Pull-Up", "muscle_group": "Back", "equipment": "Bodyweight", "instructions": "Hang from a pull-up bar with an overhand grip. Pull yourself up until your chin is above the bar, then lower back down with control.", "is_system": True},
    {"name": "Barbell Row", "muscle_group": "Back", "equipment": "Barbell", "instructions": "Bend at the hips with a slight knee bend, grip the barbell. Pull the bar to your lower chest, squeezing your shoulder blades together.", "is_system": True},
    {"name": "Seated Cable Row", "muscle_group": "Back", "equipment": "Cable", "instructions": "Sit at a cable row station with feet on the platform. Pull the handle to your midsection, squeezing your back muscles.", "is_system": True},
    {"name": "Lat Pulldown", "muscle_group": "Back", "equipment": "Cable", "instructions": "Sit at a lat pulldown machine, grip the bar wider than shoulder-width. Pull the bar down to your upper chest, then slowly return.", "is_system": True},
    {"name": "Dumbbell Single-Arm Row", "muscle_group": "Back", "equipment": "Dumbbell", "instructions": "Place one knee and hand on a bench. With the other hand, row a dumbbell to your hip, squeezing your lat at the top.", "is_system": True},

    # Shoulders
    {"name": "Overhead Press", "muscle_group": "Shoulders", "equipment": "Barbell", "instructions": "Stand with feet shoulder-width apart, press the barbell from shoulder height to full overhead extension.", "is_system": True},
    {"name": "Dumbbell Lateral Raise", "muscle_group": "Shoulders", "equipment": "Dumbbell", "instructions": "Stand with dumbbells at your sides. Raise the weights out to the sides until your arms are parallel to the floor.", "is_system": True},
    {"name": "Face Pull", "muscle_group": "Shoulders", "equipment": "Cable", "instructions": "Set a cable at upper chest height with a rope attachment. Pull the rope toward your face, separating the ends and squeezing your rear delts.", "is_system": True},
    {"name": "Arnold Press", "muscle_group": "Shoulders", "equipment": "Dumbbell", "instructions": "Start with dumbbells in front of your shoulders, palms facing you. Rotate your palms outward as you press the weights overhead.", "is_system": True},
    {"name": "Dumbbell Front Raise", "muscle_group": "Shoulders", "equipment": "Dumbbell", "instructions": "Stand with dumbbells in front of your thighs. Raise one or both dumbbells to shoulder height with straight arms.", "is_system": True},

    # Legs
    {"name": "Barbell Squat", "muscle_group": "Legs", "equipment": "Barbell", "instructions": "Place the barbell on your upper back. Squat down by bending your knees and hips until your thighs are parallel to the floor, then stand back up.", "is_system": True},
    {"name": "Romanian Deadlift", "muscle_group": "Legs", "equipment": "Barbell", "instructions": "Hold a barbell at hip height. Hinge at the hips, lowering the bar along your legs while keeping a slight knee bend. Return to standing.", "is_system": True},
    {"name": "Leg Press", "muscle_group": "Legs", "equipment": "Machine", "instructions": "Sit in the leg press machine with feet shoulder-width apart on the platform. Lower the weight by bending your knees, then press back up.", "is_system": True},
    {"name": "Walking Lunge", "muscle_group": "Legs", "equipment": "Dumbbell", "instructions": "Hold dumbbells at your sides. Step forward into a lunge, lowering your back knee toward the floor. Push off and step forward with the other leg.", "is_system": True},
    {"name": "Leg Curl", "muscle_group": "Legs", "equipment": "Machine", "instructions": "Lie face down on a leg curl machine. Curl the weight up by bending your knees, squeezing your hamstrings at the top.", "is_system": True},
    {"name": "Leg Extension", "muscle_group": "Legs", "equipment": "Machine", "instructions": "Sit in a leg extension machine. Extend your legs until they are straight, squeezing your quadriceps at the top.", "is_system": True},
    {"name": "Calf Raise", "muscle_group": "Legs", "equipment": "Machine", "instructions": "Stand on a calf raise machine with the balls of your feet on the platform. Raise your heels as high as possible, then lower slowly.", "is_system": True},

    # Arms
    {"name": "Barbell Curl", "muscle_group": "Arms", "equipment": "Barbell", "instructions": "Stand with a barbell using an underhand grip. Curl the bar up to shoulder height, keeping your elbows at your sides.", "is_system": True},
    {"name": "Tricep Pushdown", "muscle_group": "Arms", "equipment": "Cable", "instructions": "Stand at a cable station with a straight bar or rope attachment. Push the weight down by extending your elbows, keeping upper arms stationary.", "is_system": True},
    {"name": "Dumbbell Hammer Curl", "muscle_group": "Arms", "equipment": "Dumbbell", "instructions": "Stand with dumbbells at your sides, palms facing each other. Curl the weights up while maintaining the neutral grip.", "is_system": True},
    {"name": "Skull Crusher", "muscle_group": "Arms", "equipment": "Barbell", "instructions": "Lie on a bench holding an EZ bar above your chest. Lower the bar toward your forehead by bending your elbows, then extend back up.", "is_system": True},
    {"name": "Concentration Curl", "muscle_group": "Arms", "equipment": "Dumbbell", "instructions": "Sit on a bench with a dumbbell, brace your elbow against your inner thigh. Curl the weight up, squeezing your bicep at the top.", "is_system": True},

    # Core
    {"name": "Plank", "muscle_group": "Core", "equipment": "Bodyweight", "instructions": "Hold a push-up position with your forearms on the ground. Keep your body in a straight line from head to heels.", "is_system": True},
    {"name": "Cable Woodchop", "muscle_group": "Core", "equipment": "Cable", "instructions": "Set a cable at high position. Pull the handle diagonally across your body from high to low, rotating your torso.", "is_system": True},
    {"name": "Hanging Leg Raise", "muscle_group": "Core", "equipment": "Bodyweight", "instructions": "Hang from a pull-up bar. Raise your legs until they are parallel to the floor or higher, then lower with control.", "is_system": True},
    {"name": "Russian Twist", "muscle_group": "Core", "equipment": "Bodyweight", "instructions": "Sit on the floor with knees bent and feet elevated. Rotate your torso side to side, optionally holding a weight.", "is_system": True},
    {"name": "Ab Rollout", "muscle_group": "Core", "equipment": "Other", "instructions": "Kneel on the floor holding an ab wheel. Roll forward extending your body, then use your core to pull yourself back to the starting position.", "is_system": True},
]

SYSTEM_TEMPLATES = [
    {
        "name": "Push Day",
        "exercises": [
            "Barbell Bench Press",
            "Incline Dumbbell Press",
            "Overhead Press",
            "Dumbbell Lateral Raise",
            "Tricep Pushdown",
            "Skull Crusher",
        ],
    },
    {
        "name": "Pull Day",
        "exercises": [
            "Barbell Deadlift",
            "Pull-Up",
            "Barbell Row",
            "Lat Pulldown",
            "Barbell Curl",
            "Dumbbell Hammer Curl",
            "Face Pull",
        ],
    },
    {
        "name": "Leg Day",
        "exercises": [
            "Barbell Squat",
            "Romanian Deadlift",
            "Leg Press",
            "Walking Lunge",
            "Leg Curl",
            "Leg Extension",
            "Calf Raise",
        ],
    },
    {
        "name": "Upper Body",
        "exercises": [
            "Barbell Bench Press",
            "Barbell Row",
            "Overhead Press",
            "Pull-Up",
            "Dumbbell Lateral Raise",
            "Barbell Curl",
            "Tricep Pushdown",
        ],
    },
    {
        "name": "Lower Body",
        "exercises": [
            "Barbell Squat",
            "Romanian Deadlift",
            "Leg Press",
            "Walking Lunge",
            "Leg Curl",
            "Calf Raise",
        ],
    },
    {
        "name": "Full Body",
        "exercises": [
            "Barbell Squat",
            "Barbell Bench Press",
            "Barbell Row",
            "Overhead Press",
            "Barbell Deadlift",
            "Barbell Curl",
            "Plank",
        ],
    },
]


async def seed_admin(session) -> None:
    result = await session.execute(
        select(User).where(User.username == ADMIN_USER["username"])
    )
    existing = result.scalars().first()
    if existing:
        print(f"  Admin user '{ADMIN_USER['username']}' already exists. Skipping.")
        return

    admin = User(
        display_name=ADMIN_USER["display_name"],
        email=ADMIN_USER["email"],
        username=ADMIN_USER["username"],
        password_hash=hash_password(ADMIN_USER["password"]),
        role=ADMIN_USER["role"],
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    print(f"  Created admin user: {ADMIN_USER['username']} / {ADMIN_USER['password']}")


async def seed_exercises(session) -> dict:
    exercise_map = {}

    result = await session.execute(select(Exercise))
    existing_exercises = {ex.name: ex for ex in result.scalars().all()}

    created_count = 0
    skipped_count = 0

    for ex_data in EXERCISES:
        if ex_data["name"] in existing_exercises:
            exercise_map[ex_data["name"]] = existing_exercises[ex_data["name"]]
            skipped_count += 1
            continue

        exercise = Exercise(
            name=ex_data["name"],
            muscle_group=ex_data["muscle_group"],
            equipment=ex_data["equipment"],
            instructions=ex_data.get("instructions"),
            is_system=ex_data.get("is_system", True),
            created_by=None,
        )
        session.add(exercise)
        await session.flush()
        exercise_map[ex_data["name"]] = exercise
        created_count += 1

    print(f"  Exercises: {created_count} created, {skipped_count} already existed.")
    return exercise_map


async def seed_templates(session, exercise_map: dict) -> None:
    created_count = 0
    skipped_count = 0

    for tmpl_data in SYSTEM_TEMPLATES:
        result = await session.execute(
            select(WorkoutTemplate).where(
                WorkoutTemplate.name == tmpl_data["name"],
                WorkoutTemplate.is_system == True,
            )
        )
        existing = result.scalars().first()
        if existing:
            skipped_count += 1
            continue

        template = WorkoutTemplate(
            name=tmpl_data["name"],
            user_id=None,
            is_system=True,
            description=None,
        )
        session.add(template)
        await session.flush()

        for idx, exercise_name in enumerate(tmpl_data["exercises"]):
            exercise = exercise_map.get(exercise_name)
            if exercise is None:
                result = await session.execute(
                    select(Exercise).where(Exercise.name == exercise_name)
                )
                exercise = result.scalars().first()

            if exercise is None:
                print(f"    WARNING: Exercise '{exercise_name}' not found for template '{tmpl_data['name']}'. Skipping.")
                continue

            template_exercise = TemplateExercise(
                template_id=template.id,
                exercise_id=exercise.id,
                order_index=idx,
                sets_count=3,
                default_reps=10,
                default_weight=None,
            )
            session.add(template_exercise)

        await session.flush()
        created_count += 1

    print(f"  Templates: {created_count} created, {skipped_count} already existed.")


async def run_seed() -> None:
    print("Starting database seed...")
    print()

    print("Creating tables...")
    await create_tables()
    print("Tables created.")
    print()

    async with async_session_maker() as session:
        try:
            print("Seeding admin user...")
            await seed_admin(session)
            print()

            print("Seeding exercises...")
            exercise_map = await seed_exercises(session)
            print()

            print("Seeding system templates...")
            await seed_templates(session, exercise_map)
            print()

            await session.commit()
            print("Seed completed successfully!")

        except Exception as e:
            await session.rollback()
            print(f"Seed failed with error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())