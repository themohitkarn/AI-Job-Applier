"""Database session management and schema initialization."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import Base

logger = get_logger("db")

settings = get_settings()

# Engine creation with check_same_thread=False for SQLite
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables and create schemas if not present."""
    logger.info("Initializing database schemas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safely migrate new columns to job_sync_records if using SQLite
        if "sqlite" in settings.database_url:
            from sqlalchemy import text
            for col in ["jobs_parsed", "jobs_rejected", "jobs_duplicate"]:
                try:
                    await conn.execute(text(f"ALTER TABLE job_sync_records ADD COLUMN {col} INTEGER DEFAULT 0"))
                except Exception:
                    pass  # Column already exists
    logger.info("Database schemas initialized successfully.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing transactional async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error, rolled back: {e}")
            raise
        finally:
            await session.close()
