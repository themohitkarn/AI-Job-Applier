"""Database session management and schema initialization."""
import asyncio
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

# Engine creation with check_same_thread=False and increased timeout for SQLite
connect_args = {}
if "sqlite" in settings.database_url:
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 60.0

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
    future=True,
)

# Configure SQLite PRAGMAs for concurrency (WAL mode + busy timeout)
if "sqlite" in settings.database_url:
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=60000")
            cursor.close()
        except Exception:
            pass

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
        # Enable WAL mode and configure busy timeout for high concurrency
        if "sqlite" in settings.database_url:
            from sqlalchemy import text
            try:
                await conn.execute(text("PRAGMA journal_mode=WAL;"))
                await conn.execute(text("PRAGMA synchronous=NORMAL;"))
                await conn.execute(text("PRAGMA busy_timeout=60000;"))
            except Exception:
                pass
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


async def commit_with_retry(session: AsyncSession, max_retries: int = 4, delay: float = 0.25) -> None:
    """Commit an async database session with automatic exponential retry on transient SQLite locked errors."""
    for attempt in range(max_retries):
        try:
            await session.commit()
            return
        except Exception as e:
            err_msg = str(e).lower()
            if ("database is locked" in err_msg or "locked" in err_msg or "busy" in err_msg) and attempt < max_retries - 1:
                wait_time = delay * (attempt + 1)
                logger.warning(
                    f"SQLite database is locked, retrying commit in {wait_time:.2f}s "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
            else:
                raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing transactional async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await commit_with_retry(session)
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error, rolled back: {e}")
            raise
        finally:
            await session.close()
