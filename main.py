"""Main FastAPI Application Entrypoint."""
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import init_db
from app.scheduler.manager import get_scheduler
from app.web.dashboard import router as web_router

settings = get_settings()
logger = configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: Initialize database schema and background scheduler."""
    logger.info(f"Starting {settings.app_name} in [{settings.app_env}] environment...")
    
    # 1. Initialize DB tables
    await init_db()

    # 2. Start background worker scheduler
    scheduler = get_scheduler()
    scheduler.start()

    logger.info("Application startup sequence completed successfully.")
    yield

    # 3. Shutdown sequence
    logger.info("Stopping application background services...")
    await scheduler.stop()
    logger.info("Shutdown completed.")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Modular AI-Powered Job Discovery, Transparent Matching, and Human-in-the-Loop Browser Automation Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Security Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Web Dashboard and API routes
app.include_router(web_router)
app.include_router(api_v1_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
