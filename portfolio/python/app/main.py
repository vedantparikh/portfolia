import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database.connection import create_tables, init_db
from app.core.database.init_db import init_database
from app.core.logging_config import get_logger, setup_logging
from app.health_check import router as health_router

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

        # Run database migrations and create schemas
        logger.info("🔄 Running database migrations and creating schemas...")
        migration_start_time = time.time()
        await create_tables()
        migration_time = time.time() - migration_start_time
        logger.info(f"✅ Database migrations completed in {migration_time:.3f}s")

        # Initialize database with sample data if needed
        logger.info("📊 Initializing database with sample data...")
        data_start_time = time.time()
        await init_database()
        data_init_time = time.time() - data_start_time
        logger.info(f"✅ Sample data initialization completed in {data_init_time:.3f}s")

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
    shutdown_start_time = time.time()
    logger.info("🛑 Shutting down Portfolia API...")

    # Log final statistics
    total_uptime = time.time() - startup_time
    logger.info(f"📈 Total application uptime: {total_uptime:.3f}s")
    logger.info("👋 Portfolia API shutdown complete")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="Portfolia API",
    description="Portfolio management and trading strategy API",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
logger.info("🔗 Including application routers...")
app.include_router(health_router, prefix="/health", tags=["health"])
logger.info("✅ Health router included at /health")

# Include API v1 routers
try:
    from api.v1.health_router import router as health_router

    app.include_router(health_router, prefix="/api/v1", tags=["test"])
    logger.info("✅ Test router included at /api/v1")
except ImportError as e:
    logger.warning(f"⚠️ Could not import test router: {e}")

# Include authentication router
try:
    logger.info("🔐 Attempting to import auth router...")
    from api.v1.auth.router import router as auth_router

    logger.info("✅ Auth router imported successfully")
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])
    logger.info("✅ Auth router included at /api/v1/auth")
except ImportError as e:
    logger.warning(f"⚠️ Could not import auth router: {e}")
    logger.error(f"❌ Auth router import error details: {e}")
    import traceback

    logger.error(f"❌ Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"❌ Unexpected error importing auth router: {e}")
    import traceback

    logger.error(f"❌ Full traceback: {traceback.format_exc()}")

# Include market router
try:
    logger.info("📈 Attempting to import market router...")
    from api.v1.market.routers import router as market_router

    app.include_router(market_router, prefix="/api/v1", tags=["market-data"])
    logger.info("Market router included successfully")
except ImportError as e:
    logger.warning(f"Could not import market router: {e}")

# Include statistical indicators router
try:
    from api.v1.statistical_indicators.routers import router as indicators_router

    app.include_router(
        indicators_router, prefix="/api/v1", tags=["statistical-indicators"]
    )
    logger.info("Statistical indicators router included successfully")
except ImportError as e:
    logger.warning(f"Could not import statistical indicators router: {e}")

# Include portfolio router
try:
    from api.v1.portfolio.router import router as portfolio_router

    app.include_router(portfolio_router, prefix="/api/v1", tags=["portfolios"])
    logger.info("Portfolio router included successfully")
except ImportError as e:
    logger.warning(f"Could not import portfolio router: {e}")
    logger.error(f"Portfolio router import error details: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"Unexpected error importing portfolio router: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")

# Include assets router
try:
    from api.v1.assets.router import router as assets_router

    app.include_router(assets_router, prefix="/api/v1", tags=["assets"])
    logger.info("Assets router included successfully")
except ImportError as e:
    logger.warning(f"Could not import assets router: {e}")
    logger.error(f"Assets router import error details: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"Unexpected error importing assets router: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")

# Include transactions router
try:
    from api.v1.transactions.router import router as transactions_router

    app.include_router(transactions_router, prefix="/api/v1", tags=["transactions"])
    logger.info("Transactions router included successfully")
except ImportError as e:
    logger.warning(f"Could not import transactions router: {e}")
    logger.error(f"Transactions router import error details: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"Unexpected error importing transactions router: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")

# Include analytics router
try:
    from api.v1.analytics.router import router as analytics_router

    app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
    logger.info("Analytics router included successfully")
except ImportError as e:
    logger.warning(f"Could not import analytics router: {e}")
    logger.error(f"Analytics router import error details: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"Unexpected error importing analytics router: {e}")
    import traceback

    logger.error(f"Full traceback: {traceback.format_exc()}")

# Include watchlist router
try:
    logger.info("👀 Attempting to import watchlist router...")
    from api.v1.watchlist.router import router as watchlist_router

    logger.info("✅ Watchlist router imported successfully")
    app.include_router(
        watchlist_router, prefix="/api/v1/watchlists", tags=["watchlists"]
    )
    logger.info("✅ Watchlist router included at /api/v1/watchlists")
except ImportError as e:
    logger.warning(f"⚠️ Could not import watchlist router: {e}")
    logger.error(f"❌ Watchlist router import error details: {e}")
    import traceback

    logger.error(f"❌ Full traceback: {traceback.format_exc()}")
except Exception as e:
    logger.error(f"❌ Unexpected error importing watchlist router: {e}")
    import traceback

    logger.error(f"❌ Full traceback: {traceback.format_exc()}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Portfolia API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api/v1/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Portfolia API v1",
        "endpoints": {"health": "/health", "test": "/api/v1/test", "docs": "/docs"},
    }


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
