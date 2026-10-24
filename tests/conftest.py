"""Pytest global fixtures and configuration."""
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set testing environment variables before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["GROQ_API_KEY"] = "gsk_dummy_test_key_for_unit_tests_1234567890"

from app.core.config import Settings, get_settings, reset_settings
from app.db.models import Base, UserProfile
from main import app


@pytest.fixture(autouse=True)
def setup_test_env():
    """Ensure clean settings before and after each test."""
    os.environ["APP_ENV"] = "testing"
    reset_settings()
    yield
    reset_settings()


@pytest_asyncio.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite async test database session."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        # Prepopulate default test candidate profile
        prof = UserProfile(
            full_name="Alex Engineer",
            email="alex@example.com",
            phone="+1234567890",
            location="Remote",
            skills='["Python", "FastAPI", "SQLAlchemy", "Docker"]',
            experience_years=4.0,
            experiences='[{"title": "Software Engineer", "company": "Acme Inc", "responsibilities": ["FastAPI services"]}]',
            educations='[{"degree": "B.S. Computer Science", "institution": "State University"}]',
            certifications='["AWS Certified"]',
            work_authorization="Eligible to work in US/EU",
            target_roles='["Backend Developer", "Software Engineer"]',
        )
        session.add(prof)
        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
