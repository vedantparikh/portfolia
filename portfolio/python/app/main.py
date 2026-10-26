import os
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from config import settings
from core.database.connection import init_db
from core.error_handlers import install_error_handlers
from core.logging_config import get_logger, setup_logging
from health_check import router as health_router

# Setup comprehensive logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE"),
    log_dir=os.getenv("LOG_DIR", "logs"),
    enable_console=True,
    enable_file=True,
    enable_json=os.getenv("LOG_JSON", "false").lower() == "true",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - runs on startup and shutdown."""
    startup_time = time.time()

    # Startup
    logger.info("🚀 Starting Portfolia API...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(
        f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else '***'}"
    )
    logger.info(
        f"Redis URL: {settings.REDIS_URL.split('@')[1] if '@' in settings.REDIS_URL else '***'}"
    )

    try:
        # Initialize database connection
        logger.info("🔌 Initializing database connection...")
        db_start_time = time.time()
        await init_db()
        db_init_time = time.time() - db_start_time
        logger.info(
            f"✅ Database connection initialized successfully in {db_init_time:.3f}s"
        )

        total_startup_time = time.time() - startup_time
        logger.info(
            f"🎉 Database initialization completed successfully in {total_startup_time:.3f}s total!"
        )

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        # Don't fail startup - allow app to run with degraded functionality
        logger.warning("⚠️ Application starting with degraded database functionality")
        logger.warning(f"Startup time so far: {time.time() - startup_time:.3f}s")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Portfolia API...")

    # Log final statistics
    total_uptime = time.time() - startup_time
    logger.info(f"📈 Total application uptime: {total_uptime:.3f}s")
    logger.info("👋 Portfolia API shutdown complete")


async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Portfolia API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


async def api_root():
    """API root endpoint."""
    return {
        "message": "Portfolia API v1",
        "endpoints": {"health": "/health", "test": "/api/v1/test", "docs": "/docs"},
    }


def _operation_id(route: APIRoute) -> str:
    """One id per method and path, so two handlers with the same name do not collide."""
    method = sorted(route.methods)[0].lower()
    slug = re.sub(r"\W+", "_", route.path_format).strip("_")
    return f"{method}_{slug}"


def create_app() -> FastAPI:
    """Build the API. Router imports are explicit and a failure stops startup."""
    from api.v1.router import build_v1_router

    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Portfolio management and trading strategy API",
        version=settings.VERSION,
        lifespan=lifespan,
        generate_unique_id_function=_operation_id,
    )
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        # Browsers reject credentialed requests to a wildcard origin; never allow both.
        allow_credentials="*" not in settings.ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Including application routers")
    application.include_router(health_router, prefix="/health")
    application.include_router(build_v1_router())
    application.add_api_route("/", root, methods=["GET"], tags=["meta"])
    application.add_api_route("/api/v1/", api_root, methods=["GET"], tags=["meta"])
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
