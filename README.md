# FitLog Workout Tracker

A comprehensive workout tracking API built with Python and FastAPI, designed to help users log workouts, track exercises, monitor progress, and achieve fitness goals.

## Features

- **User Authentication** — Secure registration and login with JWT-based authentication
- **Workout Logging** — Create, read, update, and delete workout sessions
- **Exercise Management** — Browse and manage a library of exercises with muscle group categorization
- **Set Tracking** — Log individual sets with weight, reps, duration, and distance metrics
- **Progress Monitoring** — Track personal records and workout history over time
- **Workout Templates** — Save and reuse workout routines as templates
- **RESTful API** — Clean, well-documented API endpoints following REST conventions

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (via aiosqlite for async) / PostgreSQL (via asyncpg for production)
- **ORM:** SQLAlchemy 2.0 (async)
- **Authentication:** JWT (python-jose) + bcrypt password hashing
- **Validation:** Pydantic v2
- **Configuration:** pydantic-settings with `.env` support
- **Testing:** pytest + pytest-asyncio + httpx

## Folder Structure

```
fitlog-workout-tracker/
├── app/
│   ├── core/
│   │   ├── config.py          # Application settings (env vars)
│   │   ├── database.py        # Async SQLAlchemy engine & session
│   │   ├── security.py        # JWT token creation & password hashing
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── exercise.py        # Exercise model
│   │   ├── workout.py         # Workout & WorkoutExercise models
│   │   ├── workout_set.py     # WorkoutSet model
│   │   ├── template.py        # WorkoutTemplate model
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py            # User request/response schemas
│   │   ├── exercise.py        # Exercise schemas
│   │   ├── workout.py         # Workout schemas
│   │   ├── workout_set.py     # WorkoutSet schemas
│   │   ├── template.py        # Template schemas
│   │   └── __init__.py
│   ├── services/
│   │   ├── user_service.py    # User business logic
│   │   ├── exercise_service.py# Exercise business logic
│   │   ├── workout_service.py # Workout business logic
│   │   ├── template_service.py# Template business logic
│   │   └── __init__.py
│   ├── dependencies/
│   │   ├── auth.py            # Authentication dependencies
│   │   └── __init__.py
│   ├── routers/
│   │   ├── auth.py            # Auth routes (register, login)
│   │   ├── users.py           # User profile routes
│   │   ├── exercises.py       # Exercise CRUD routes
│   │   ├── workouts.py        # Workout CRUD routes
│   │   ├── templates.py       # Template routes
│   │   └── __init__.py
│   └── main.py                # FastAPI app entry point
├── tests/
│   ├── test_auth.py           # Authentication tests
│   ├── test_exercises.py      # Exercise endpoint tests
│   ├── test_workouts.py       # Workout endpoint tests
│   └── conftest.py            # Shared test fixtures
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── README.md                  # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fitlog-workout-tracker
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update values as needed:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy async database URL | `sqlite+aiosqlite:///./fitlog.db` |
| `SECRET_KEY` | JWT signing secret (use a strong random string) | `change-me-to-a-random-secret-key` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration in minutes | `1440` |
| `ENVIRONMENT` | Runtime environment (`development`, `production`) | `development` |

### 5. Run Database Migrations / Seed

The database tables are created automatically on application startup via SQLAlchemy's `create_all`. No manual migration step is required for initial setup.

To seed the database with sample exercises:

```bash
python -m app.seed
```

### 6. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive API documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

## API Endpoints Summary

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive JWT token |

### Users

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users/me` | Get current user profile |
| `PUT` | `/api/users/me` | Update current user profile |

### Exercises

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/exercises` | List all exercises (with filters) |
| `POST` | `/api/exercises` | Create a new exercise |
| `GET` | `/api/exercises/{id}` | Get exercise by ID |
| `PUT` | `/api/exercises/{id}` | Update an exercise |
| `DELETE` | `/api/exercises/{id}` | Delete an exercise |

### Workouts

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/workouts` | List user's workouts (paginated) |
| `POST` | `/api/workouts` | Create a new workout |
| `GET` | `/api/workouts/{id}` | Get workout details with exercises and sets |
| `PUT` | `/api/workouts/{id}` | Update a workout |
| `DELETE` | `/api/workouts/{id}` | Delete a workout |
| `POST` | `/api/workouts/{id}/exercises` | Add exercise to workout |
| `POST` | `/api/workouts/{id}/exercises/{exercise_id}/sets` | Add set to workout exercise |

### Workout Templates

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/templates` | List user's workout templates |
| `POST` | `/api/templates` | Create a template from a workout |
| `GET` | `/api/templates/{id}` | Get template details |
| `POST` | `/api/templates/{id}/start` | Start a workout from a template |
| `DELETE` | `/api/templates/{id}` | Delete a template |

## Running Tests

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing -v
```

## Deployment Guide

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t fitlog-tracker .
docker run -p 8000:8000 --env-file .env fitlog-tracker
```

### Production Considerations

- Set `ENVIRONMENT=production` in your environment variables
- Use a strong, unique `SECRET_KEY` (generate with `openssl rand -hex 32`)
- Switch `DATABASE_URL` to PostgreSQL for production: `postgresql+asyncpg://user:pass@host:5432/fitlog`
- Run behind a reverse proxy (nginx, Caddy) with HTTPS
- Configure CORS `allow_origins` to your frontend domain(s)
- Use a process manager like `gunicorn` with uvicorn workers:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```

## License

Private — All rights reserved.