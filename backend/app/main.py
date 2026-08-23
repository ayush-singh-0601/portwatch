"""
FastAPI application factory and entry point.

Run with::

    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = logging.getLogger("portwatch")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — runs on startup and shutdown.

    Startup:
        - Configures logging level based on APP_DEBUG.
        - Logs the active configuration summary.

    Shutdown:
        - Disposes the async database engine connection pool.
    """
    # ── Startup ────────────────────────────────────────────────────
    log_level = logging.DEBUG if settings.APP_DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    logger.info("=" * 60)
    logger.info("PortWatch API starting up")
    logger.info("  Environment : %s", settings.APP_ENV)
    logger.info("  Debug       : %s", settings.APP_DEBUG)
    logger.info("  Mock data   : %s", settings.MOCK_DATA_MODE)
    logger.info("  Database    : %s", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "***")
    logger.info("  AISStream   : %s", "configured" if settings.AISSTREAM_API_KEY else "not configured")
    logger.info("=" * 60)

    # Start live AIS Ingest worker if Mock Data Mode is disabled
    if not settings.MOCK_DATA_MODE:
        logger.info("Mock Data Mode is DISABLED — starting real-time AIS Ingestion background worker...")
        from app.services.ais_ingestion import ingestion_service
        await ingestion_service.start()

    yield

    # ── Shutdown ───────────────────────────────────────────────────
    if not settings.MOCK_DATA_MODE:
        logger.info("Stopping real-time AIS Ingestion background worker...")
        from app.services.ais_ingestion import ingestion_service
        try:
            await ingestion_service.stop()
        except Exception as exc:
            logger.error("Error stopping AIS Ingest worker during shutdown: %s", exc)

    logger.info("PortWatch API shutting down — disposing database engine")
    from app.database import engine

    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title="PortWatch API",
        description=(
            "Maritime OSINT platform for vessel tracking, sanctions screening, "
            "dark-activity detection, ownership analysis, and risk scoring."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────
    from app.routers import enriched, ownership, positions, reports, risk, sanctions, vessels, ws

    app.include_router(enriched.router)
    app.include_router(vessels.router)
    app.include_router(positions.router)
    app.include_router(ownership.router)
    app.include_router(sanctions.router)
    app.include_router(risk.router)
    app.include_router(reports.router)
    app.include_router(ws.router)

    # ── Health check ───────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "portwatch-api"}

    return app


# Application instance — used by ``uvicorn app.main:app``
app = create_app()
