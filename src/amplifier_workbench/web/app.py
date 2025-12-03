"""FastAPI application for Amplifier Workbench."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from amplifier_workbench.core import SessionManager

from .routes import collections_router, configs_router, modules_router, profiles_router, sessions_router

logger = logging.getLogger(__name__)

# Global session manager for cleanup
_session_manager: SessionManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Amplifier Workbench API")
    yield
    # Cleanup on shutdown
    logger.info("Shutting down Amplifier Workbench API")
    from .routes.sessions import get_session_manager

    manager = get_session_manager()
    await manager.stop_all()


def create_app(
    title: str = "Amplifier Workbench",
    debug: bool = False,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """
    Create the FastAPI application.

    Args:
        title: API title
        debug: Enable debug mode
        cors_origins: Allowed CORS origins (defaults to ["*"] in debug mode)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description="Interactive mount plan builder and tester for Amplifier",
        version="0.1.0",
        lifespan=lifespan,
        debug=debug,
    )

    # Configure CORS
    origins = cors_origins or (["*"] if debug else ["http://localhost:3000"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(collections_router, prefix="/api")
    app.include_router(modules_router, prefix="/api")
    app.include_router(profiles_router, prefix="/api")
    app.include_router(configs_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": title,
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# For running with uvicorn directly
app = create_app(debug=True)
