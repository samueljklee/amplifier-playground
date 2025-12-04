"""FastAPI application for Amplifier Playground."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from amplifier_playground.core import SessionManager, load_credentials_to_env

from .routes import collections_router, configs_router, modules_router, profiles_router, sessions_router
from .routes.settings import router as settings_router

# Path to bundled frontend static files
STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger(__name__)

# Global session manager for cleanup
_session_manager: SessionManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Amplifier Playground API")

    # Load stored credentials into environment
    loaded = load_credentials_to_env()
    if loaded:
        logger.info(f"Loaded credentials from config: {', '.join(loaded.keys())}")

    yield
    # Cleanup on shutdown
    logger.info("Shutting down Amplifier Playground API")
    from .routes.sessions import get_session_manager, signal_shutdown

    # Signal SSE connections to terminate first
    await signal_shutdown()

    manager = get_session_manager()
    await manager.stop_all()


def create_app(
    title: str = "Amplifier Playground",
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
    app.include_router(settings_router, prefix="/api")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    # Serve frontend static files if available
    if STATIC_DIR.exists():
        # Mount static assets (js, css, etc.)
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/")
        async def serve_index():
            """Serve the frontend index.html."""
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"name": title, "version": "0.1.0", "docs": "/docs"}

        # Catch-all for SPA routing - must be registered last
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve index.html for SPA routes (but not API routes)."""
            # Don't intercept API routes
            if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
                return {"error": "Not found"}
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"error": "Frontend not available"}
    else:
        @app.get("/")
        async def root():
            """Root endpoint with API info (no frontend bundled)."""
            return {
                "name": title,
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/health",
                "note": "Frontend not bundled. Run 'npm run build' in frontend/ and copy dist/ to web/static/",
            }

    return app


# For running with uvicorn directly
app = create_app(debug=True)
