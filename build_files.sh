#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database setup..."
python -c "
import asyncio
from app.core.database import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(init_db())
"

echo "Creating static directories if needed..."
mkdir -p static

echo "Build completed successfully."