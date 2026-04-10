# FitLog Workout Tracker — Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Vercel Deployment](#vercel-deployment)
- [Database Considerations for Serverless](#database-considerations-for-serverless)
- [Build Script Details](#build-script-details)
- [CI/CD Notes](#cicd-notes)
- [Troubleshooting](#troubleshooting)

---

## Overview

FitLog Workout Tracker is a Python FastAPI application designed to track workouts, exercises, and fitness progress. This document covers deployment to Vercel and other environments, environment variable configuration, database setup, and common troubleshooting steps.

---

## Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)
- **Git** for version control
- **Vercel CLI** (`npm i -g vercel`) for Vercel deployments
- A **PostgreSQL** database (recommended for production) or **SQLite** (development only)

---

## Environment Variables

Create a `.env` file in the project root for local development. For production, set these variables in your hosting provider's dashboard.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./fitlog.db` | Async database connection string |
| `SECRET_KEY` | Yes | — | Secret key for JWT token signing. Generate with `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token expiration in minutes |
| `ENVIRONMENT` | No | `development` | `development`, `staging`, or `production` |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of allowed CORS origins |
| `LOG_LEVEL` | No | `info` | Logging level: `debug`, `info`, `warning`, `error` |

### Example `.env` file

```env
DATABASE_URL=sqlite+aiosqlite:///./fitlog.db
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
LOG_LEVEL=info
```

### Production Database URL Examples

**PostgreSQL (recommended):**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/fitlog
```

**SQLite (development only):**
```
DATABASE_URL=sqlite+aiosqlite:///./fitlog.db
```

> **Important:** Never commit `.env` files to version control. The `.gitignore` file should include `.env`.

---

## Local Development

### 1. Clone the repository

```bash
git clone <repository-url>
cd fitlog-workout-tracker
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your values
```

### 5. Run the application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### 6. Run tests

```bash
pytest -v
```

---

## Vercel Deployment

### Project Structure for Vercel

Vercel requires a `vercel.json` configuration file in the project root to handle Python ASGI applications.

### 1. Create `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### 2. Set environment variables in Vercel

Navigate to your Vercel project dashboard:

1. Go to **Settings** → **Environment Variables**
2. Add each variable from the [Environment Variables](#environment-variables) table
3. Set `ENVIRONMENT` to `production`
4. Set `DATABASE_URL` to your production PostgreSQL connection string
5. Generate a strong `SECRET_KEY` and add it

> **Critical:** The `SECRET_KEY` must be a strong, unique value in production. Generate one with `openssl rand -hex 32`.

### 3. Deploy via Vercel CLI

```bash
# Login to Vercel
vercel login

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### 4. Deploy via Git Integration

1. Connect your GitHub/GitLab/Bitbucket repository to Vercel
2. Vercel will automatically deploy on every push to the main branch
3. Pull requests will generate preview deployments

### Vercel-Specific Considerations

- **Cold starts:** Serverless functions have cold start latency. The first request after inactivity may take 2–5 seconds.
- **Execution timeout:** Vercel Hobby plan has a 10-second timeout; Pro plan has 60 seconds. Ensure API endpoints respond within these limits.
- **File system:** Vercel's serverless environment has a read-only file system (except `/tmp`). SQLite will **not** work in production on Vercel — use an external PostgreSQL database.
- **`extra="ignore"` in Pydantic Settings:** Vercel injects additional environment variables (`VERCEL`, `VERCEL_ENV`, `VERCEL_URL`, etc.). The application's `BaseSettings` must use `extra="ignore"` to prevent `ValidationError` from these unexpected variables.

---

## Database Considerations for Serverless

### Why Not SQLite in Production?

SQLite stores data in a local file. Serverless platforms like Vercel:
- Use ephemeral, read-only file systems
- Spin up multiple isolated instances that cannot share a local file
- Destroy instance state between invocations

**Result:** Data written to SQLite in one request may not exist in the next.

### Recommended: External PostgreSQL

Use a managed PostgreSQL service:

| Provider | Free Tier | Connection String Format |
|---|---|---|
| **Neon** | 512 MB | `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require` |
| **Supabase** | 500 MB | `postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| **Railway** | $5 credit | `postgresql+asyncpg://postgres:pass@xxx.railway.app:5432/railway` |
| **Render** | 256 MB (90 days) | `postgresql+asyncpg://user:pass@xxx.render.com/dbname` |

### Connection Pooling for Serverless

Serverless functions create new database connections on each cold start. To avoid exhausting your database's connection limit:

1. **Use connection pooling services** like PgBouncer or Neon's built-in pooler
2. **Set conservative pool sizes** in SQLAlchemy:
   ```python
   create_async_engine(
       DATABASE_URL,
       pool_size=5,
       max_overflow=10,
       pool_timeout=30,
       pool_recycle=1800,  # Recycle connections every 30 minutes
   )
   ```
3. **Use Neon's serverless driver** endpoint (append `?sslmode=require` to the connection string)

### Database Migrations

For schema changes in production:

```bash
# Generate a migration (if using Alembic)
alembic revision --autogenerate -m "description of change"

# Apply migrations
alembic upgrade head
```

> **Note:** Run migrations from a persistent environment (your local machine or a CI/CD pipeline), not from the serverless function itself.

---

## Build Script Details

### `requirements.txt`

All Python dependencies are pinned in `requirements.txt`. Key packages:

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy` | ORM and database toolkit |
| `aiosqlite` | Async SQLite driver (development) |
| `asyncpg` | Async PostgreSQL driver (production) |
| `pydantic-settings` | Environment variable management |
| `python-dotenv` | `.env` file loading |
| `python-jose[cryptography]` | JWT token handling |
| `bcrypt` | Password hashing |
| `python-multipart` | Form data parsing |
| `httpx` | Async HTTP client (testing) |
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |

### Installing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install with pip freeze for reproducibility
pip install -r requirements.txt
pip freeze > requirements.lock
```

### Running the Application

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_workouts.py -v

# Run tests matching a pattern
pytest -k "test_create" -v
```

---

## CI/CD Notes

### GitHub Actions Example

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run linting
        run: |
          pip install ruff
          ruff check app/

      - name: Run tests
        env:
          DATABASE_URL: "sqlite+aiosqlite:///./test.db"
          SECRET_KEY: "test-secret-key-not-for-production"
          ENVIRONMENT: "development"
        run: pytest -v --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: "--prod"
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `VERCEL_TOKEN` | Vercel personal access token (Settings → Tokens) |
| `VERCEL_ORG_ID` | Found in `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | Found in `.vercel/project.json` after `vercel link` |

### Branch Strategy

- **`main`** — Production branch. Merges trigger production deployment.
- **`develop`** — Integration branch. Merges trigger preview deployment.
- **Feature branches** — Create from `develop`, open PRs to `develop`.

---

## Troubleshooting

### Common Issues

#### 1. `ModuleNotFoundError: No module named 'app'`

**Cause:** Python cannot find the `app` package.

**Fix:** Ensure you are running the application from the project root directory:
```bash
cd fitlog-workout-tracker
uvicorn app.main:app --reload
```

#### 2. `ValidationError: extra fields not permitted` on Vercel

**Cause:** Vercel injects environment variables (`VERCEL`, `VERCEL_ENV`, etc.) that Pydantic's `BaseSettings` does not expect.

**Fix:** Add `extra="ignore"` to the settings configuration:
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

#### 3. `sqlalchemy.exc.OperationalError: unable to open database file`

**Cause:** SQLite cannot write to the file system (common on Vercel/serverless).

**Fix:** Use an external PostgreSQL database for production. Set `DATABASE_URL` to a PostgreSQL connection string.

#### 4. `MissingGreenlet: greenlet_spawn has not been called`

**Cause:** Lazy loading a SQLAlchemy relationship inside an async context.

**Fix:** Use `lazy="selectin"` on all relationship declarations, or use `selectinload()` in queries:
```python
from sqlalchemy.orm import selectinload
result = await db.execute(
    select(Workout).options(selectinload(Workout.exercises))
)
```

#### 5. `ConnectionRefusedError` when connecting to PostgreSQL

**Cause:** Database is not running or connection string is incorrect.

**Fix:**
- Verify the database is running and accessible
- Check `DATABASE_URL` format: `postgresql+asyncpg://user:password@host:port/dbname`
- Ensure `?sslmode=require` is appended for cloud-hosted databases
- Check that your IP is allowlisted in the database provider's dashboard

#### 6. `jose.exceptions.JWTError: Signature verification failed`

**Cause:** `SECRET_KEY` differs between the environment that issued the token and the one verifying it.

**Fix:** Ensure the same `SECRET_KEY` is set across all instances. On Vercel, set it as an environment variable — do not rely on `.env` files.

#### 7. Tests fail with `httpx.ConnectError`

**Cause:** Tests are trying to make real HTTP requests instead of using the test client.

**Fix:** Use `httpx.AsyncClient` with the app as transport:
```python
from httpx import AsyncClient, ASGITransport
from app.main import app

async with AsyncClient(
    transport=ASGITransport(app=app),
    base_url="http://test"
) as client:
    response = await client.get("/api/endpoint")
```

#### 8. `ImportError: email-validator is not installed`

**Cause:** A Pydantic schema uses `EmailStr` but `email-validator` is not installed.

**Fix:** Add `email-validator` to `requirements.txt` and reinstall:
```bash
pip install email-validator
```

#### 9. Slow cold starts on Vercel

**Cause:** Large dependency bundle or heavy initialization logic.

**Fix:**
- Minimize dependencies in `requirements.txt`
- Defer heavy initialization (database connections, etc.) to the lifespan handler
- Consider using Vercel's Pro plan for longer timeouts and better performance

#### 10. CORS errors in the browser

**Cause:** Frontend origin is not in the allowed origins list.

**Fix:** Add the frontend URL to `CORS_ORIGINS`:
```env
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

---

## Health Check

The application exposes a health check endpoint:

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

Use this endpoint for uptime monitoring and load balancer health checks.

---

## Security Checklist

Before deploying to production, verify:

- [ ] `SECRET_KEY` is a strong, unique value (at least 32 hex characters)
- [ ] `ENVIRONMENT` is set to `production`
- [ ] `CORS_ORIGINS` contains only trusted origins (no wildcards)
- [ ] `DATABASE_URL` uses SSL (`?sslmode=require`)
- [ ] `.env` file is in `.gitignore`
- [ ] All passwords are hashed with bcrypt
- [ ] JWT tokens have a reasonable expiration time
- [ ] Rate limiting is configured for authentication endpoints
- [ ] HTTPS is enforced (handled by Vercel automatically)