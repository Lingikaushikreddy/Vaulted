from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from pathlib import Path
from .models import Base

# Default to a local SQLite database in the current directory
DATABASE_URL = "sqlite+aiosqlite:///./aegis.db"

engine = create_async_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, # Needed for SQLite
    echo=False
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initializes the database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
